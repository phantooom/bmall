import requests
import json
import sqlite3
import time
import random
import argparse
from datetime import datetime

class BiliMallStatusSpider:
    def __init__(self, cookie=None):
        self.min_sleep = 0.2  # 最小休眠时间(秒)
        self.max_sleep = 0.5  # 最大休眠时间(秒)
        self.error_sleep = 30  # 错误重试休眠时间(秒)
        self.fatal_sleep = 60  # 严重错误休眠时间(秒)
        self.round_sleep = 120  # 每轮结束后的休眠时间(秒)，默认30分钟
        self.max_retry_sleep = 120  # 最大重试休眠时间(秒)，默认2小时
        self.retry_multiplier = 2  # 重试时间翻倍系数
        self.url = 'https://mall.bilibili.com/mall-magic-c/internet/c2c/items/queryC2cItemsDetail'
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'content-type': 'application/json',
            'origin': 'https://mall.bilibili.com',
            'referer': 'https://mall.bilibili.com/neul-next/index.html?page=magic-market_detail',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'
        }
        if cookie:
            self.headers['cookie'] = cookie
        self.init_db()
        self.suspicious_threshold = 20  # 1小时内上架次数阈值
        self.batch_size = 20  # 每批处理的商品数量
        self.batch_sleep = 3  # 每批处理后的休眠时间(秒)

    def init_db(self):
        """初始化数据库连接"""
        self.conn = sqlite3.connect('./db/bilibili_mall.db')
        self.cursor = self.conn.cursor()
        
        # 添加 publish_status 字段（如果不存在）
        try:
            self.cursor.execute('''
                ALTER TABLE c2c_items 
                ADD COLUMN publish_status INTEGER DEFAULT 1
            ''')
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # 字段已存在，忽略错误

    def fetch_item_status(self, item_id):
        """获取商品状态"""
        try:
            url = f"{self.url}?c2cItemsId={item_id}"
            
            delay = random.uniform(self.min_sleep, self.max_sleep)
            time.sleep(delay)
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            # 处理HTTP错误
            if response.status_code != 200:
                print(f"HTTP错误: {response.status_code}")
                time.sleep(self.error_sleep)
                return None
            
            data = response.json()
            
            # 处理API错误
            if data['code'] != 0:
                print(f"API错误: {data.get('message', '未知错误')}")
                time.sleep(self.error_sleep)
                return None
            
            # 获取状态
            publish_status = data['data'].get('publishStatus', None)
            sale_status = data['data'].get('saleStatus', None)
            
            # 如果已售出，返回特定状态码
            if sale_status == 2:
                print(f"商品 {item_id} 已售出")
                return -2  # 使用 -2 表示已售出状态
            
            return publish_status
            
        except requests.exceptions.RequestException as e:
            print(f"请求异常: {e}")
            time.sleep(self.error_sleep)
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            time.sleep(self.error_sleep)
            return None
        except Exception as e:
            print(f"获取商品状态失败: {e}")
            time.sleep(self.fatal_sleep)
            return None

    def update_item_status(self, item_id, status):
        """更新商品状态"""
        try:
            self.cursor.execute('''
                UPDATE c2c_items 
                SET publish_status = ?,
                    last_check_time = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, item_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"更新商品状态失败: {e}")
            self.conn.rollback()
            return False

    def update_check_time(self, item_id):
        """更新商品检查时间"""
        try:
            self.cursor.execute('''
                UPDATE c2c_items 
                SET last_check_time = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (item_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"更新检查时间失败: {e}")
            self.conn.rollback()
            return False

    def get_active_items(self):
        """获取需要检查的在售商品ID，优先检查未检查过的商品，然后是最早检查的商品"""
        self.cursor.execute('''
            WITH ranked_items AS (
                -- 对每个SKU的商品按价格排序
                SELECT 
                    i.id,
                    i.sku_id,
                    i.price,
                    i.last_check_time,
                    ROW_NUMBER() OVER (PARTITION BY i.sku_id ORDER BY i.price ASC) as price_rank,
                    CASE 
                        WHEN i.last_check_time IS NULL THEN 1  -- 未检查过的优先级最高
                        ELSE 2  -- 已检查过的优先级较低
                    END as check_priority
                FROM c2c_items i
                WHERE i.publish_status = 1 
                  AND (i.publish_status != -2 OR i.publish_status IS NULL)  -- 排除已售商品
            )
            SELECT 
                id,
                sku_id,
                price,
                last_check_time
            FROM ranked_items
            ORDER BY 
                check_priority ASC,  -- 优先检查未检查过的
                CASE 
                    WHEN check_priority = 1 THEN price_rank  -- 未检查过的按价格排序
                    ELSE last_check_time  -- 已检查过的按最后检查时间排序
                END ASC
        ''')
        return [(row[0], row[1], row[2]) for row in self.cursor.fetchall()]

    def check_suspicious_users(self):
        """检查并自动将可疑用户加入黑名单"""
        try:
            cursor = self.cursor
            
            # 查找可疑用户
            cursor.execute("""
                WITH user_stats AS (
                    SELECT 
                        c.uid,
                        c.uname,
                        c.sku_id,
                        COUNT(*) as listing_count,
                        MIN(c.created_at) as first_listing,
                        MAX(c.created_at) as last_listing
                    FROM c2c_items c
                    WHERE c.created_at >= datetime('now', '-1 hour')
                    GROUP BY c.uid, c.uname, c.sku_id
                    HAVING listing_count >= ?
                )
                SELECT 
                    us.*,
                    s.name as sku_name
                FROM user_stats us
                JOIN skus s ON us.sku_id = s.sku_id
                WHERE NOT EXISTS (
                    SELECT 1 FROM blacklist b 
                    WHERE b.uid = us.uid
                )
            """, (self.suspicious_threshold,))
            
            suspicious_users = cursor.fetchall()
            
            for user in suspicious_users:
                try:
                    # 添加到黑名单
                    cursor.execute("""
                        INSERT INTO blacklist (uid, uname, reason)
                        VALUES (?, ?, ?)
                    """, (
                        user['uid'],
                        user['uname'],
                        f"自动加入黑名单：1小时内对商品 {user['sku_name']} 上架 {user['listing_count']} 次"
                    ))
                    
                    print(f"用户 {user['uname']}(UID:{user['uid']}) 已自动加入黑名单")
                    print(f"原因：1小时内对商品 {user['sku_name']} 上架 {user['listing_count']} 次")
                    
                except sqlite3.IntegrityError:
                    # 用户已在黑名单中，忽略
                    pass
                
            self.conn.commit()
            
        except Exception as e:
            print(f"检查可疑用户时出错: {e}")
            self.conn.rollback()

    def run(self):
        """运行状态更新爬虫"""
        while True:  # 持续运行
            print("\n=== 开始新一轮状态更新 ===")
            start_time = datetime.now()
            
            # 获取所有在售商品
            items = self.get_active_items()
            total_items = len(items)
            updated_count = 0
            status_changed = 0
            error_count = 0
            current_retry_sleep = self.error_sleep  # 当前重试休眠时间
            
            print(f"找到 {total_items} 个在售商品，按SKU分组并优先检查最低价商品")
            
            # 按批次处理商品
            for i in range(0, len(items), self.batch_size):
                batch_items = items[i:i + self.batch_size]
                print(f"\n处理批次 {i//self.batch_size + 1}/{(total_items + self.batch_size - 1)//self.batch_size}")
                
                for idx, (item_id, sku_id, price) in enumerate(batch_items, i + 1):
                    try:
                        # 获取商品的最后检查时间
                        self.cursor.execute('''
                            SELECT last_check_time 
                            FROM c2c_items 
                            WHERE id = ?
                        ''', (item_id,))
                        result = self.cursor.fetchone()
                        last_check = result[0] if result else None
                        check_status = "从未检查" if last_check is None else f"上次检查: {last_check}"
                        
                        print(f"\n处理商品 {idx}/{total_items} (ID: {item_id}, SKU: {sku_id}, 价格: ¥{price:.2f}, {check_status})")
                        status = self.fetch_item_status(item_id)
                        
                        if status is not None:
                            if status != 1:  # 状态发生变化
                                if self.update_item_status(item_id, status):
                                    status_changed += 1
                                    print(f"商品 {item_id} 状态已更新: {'在售' if status == 1 else '已下架'}")
                            else:  # 状态未变化，仍为在售状态
                                self.update_check_time(item_id)
                            updated_count += 1
                            error_count = 0  # 重置错误计数
                            current_retry_sleep = self.error_sleep  # 重置重试时间
                        else:
                            error_count += 1
                            print(f"获取商品 {item_id} 状态失败")
                        
                        # 如果连续错误过多，增加休眠时间
                        if error_count >= 3:
                            print(f"连续出错 {error_count} 次，休眠 {current_retry_sleep} 秒...")
                            time.sleep(current_retry_sleep)
                            # 计算下一次重试时间
                            current_retry_sleep = min(
                                current_retry_sleep * self.retry_multiplier,
                                self.max_retry_sleep
                            )
                            print(f"下次重试休眠时间将增加到: {current_retry_sleep} 秒")
                            error_count = 0
                        
                    except Exception as e:
                        print(f"处理商品 {item_id} 时出错: {e}")
                        error_count += 1
                        time.sleep(current_retry_sleep)
                        # 计算下一次重试时间
                        current_retry_sleep = min(
                            current_retry_sleep * self.retry_multiplier,
                            self.max_retry_sleep
                        )
                        continue
                
                # 每批次处理完后休息
                if i + self.batch_size < total_items:
                    print(f"批次处理完成，休息 {self.batch_sleep} 秒...")
                    time.sleep(self.batch_sleep)

            end_time = datetime.now()
            duration = end_time - start_time
            
            print("\n=== 本轮更新完成 ===")
            print(f"总计处理商品: {total_items}")
            print(f"成功更新状态: {updated_count}")
            print(f"状态发生变化: {status_changed}")
            print(f"处理失败数量: {total_items - updated_count}")
            print(f"耗时: {duration}")
            
            print(f"\n等待{self.round_sleep}秒（{self.round_sleep/60:.1f}分钟）后开始下一轮...")
            time.sleep(self.round_sleep)
            
            # 在每轮结束时检查可疑用户
            print("\n=== 检查可疑用户 ===")
            self.check_suspicious_users()

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='B站商城商品状态更新爬虫')
    parser.add_argument('--cookie', type=str, required=True, help='浏览器Cookie字符串')
    parser.add_argument('--min-sleep', type=float, default=1, help='最小休眠时间(秒)，默认1秒')
    parser.add_argument('--max-sleep', type=float, default=3, help='最大休眠时间(秒)，默认3秒')
    parser.add_argument('--error-sleep', type=int, default=30, help='错误重试休眠时间(秒)，默认30秒')
    parser.add_argument('--fatal-sleep', type=int, default=60, help='严重错误休眠时间(秒)，默认60秒')
    parser.add_argument('--round-sleep', type=int, default=1800, help='每轮结束后的休眠时间(秒)，默认1800秒')
    parser.add_argument('--max-retry-sleep', type=int, default=7200, help='最大重试休眠时间(秒)，默认7200秒')
    parser.add_argument('--retry-multiplier', type=float, default=2.0, help='重试时间翻倍系数，默认2.0')
    args = parser.parse_args()

    spider = BiliMallStatusSpider(cookie=args.cookie)
    spider.min_sleep = args.min_sleep
    spider.max_sleep = args.max_sleep
    spider.error_sleep = args.error_sleep
    spider.fatal_sleep = args.fatal_sleep
    spider.round_sleep = args.round_sleep
    spider.max_retry_sleep = args.max_retry_sleep
    spider.retry_multiplier = args.retry_multiplier
    
    try:
        spider.run()
    finally:
        spider.close() 
import requests
import json
import sqlite3
from datetime import datetime
import time
import random
import argparse

class BiliMallSpider:
    def __init__(self, cookie=None):
        self.duplicate_count = 0
        self.max_duplicate_pages = 5
        self.min_sleep = 2  # 最小休眠时间(秒)
        self.max_sleep = 5  # 最大休眠时间(秒)
        self.error_sleep = 30  # 错误重试休眠时间(秒)
        self.fatal_sleep = 60  # 严重错误休眠时间(秒)
        self.url = 'https://mall.bilibili.com/mall-magic-c/internet/c2c/v2/list'
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'content-type': 'application/json',
            'origin': 'https://mall.bilibili.com',
            'referer': 'https://mall.bilibili.com/neul-next/index.html?page=magic-market_index',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'
        }
        if cookie:
            self.headers['cookie'] = cookie
        self.init_db()

    def init_db(self):
        """初始化数据库"""
        self.conn = sqlite3.connect('bilibili_mall.db')
        self.cursor = self.conn.cursor()
        
        # 创建品牌表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            keywords TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建SKU主表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS skus (
            sku_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            img TEXT,
            market_price REAL,
            type INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建商品主表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS c2c_items (
            id INTEGER PRIMARY KEY,
            type INTEGER,
            name TEXT,
            brand_id INTEGER,
            sku_id INTEGER,
            items_id INTEGER,
            total_items_count INTEGER,
            price REAL,
            show_price TEXT,
            show_market_price TEXT,
            uid TEXT,
            payment_time INTEGER,
            is_my_publish INTEGER,
            uspace_jump_url TEXT,
            uface TEXT,
            uname TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brand_id) REFERENCES brands(id),
            FOREIGN KEY (sku_id) REFERENCES skus(sku_id)
        )
        ''')
        
        # 添加索引以提高查询性能
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_id ON c2c_items(id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_sku_id ON c2c_items(sku_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_items_id ON c2c_items(items_id)')
        
        # 添加品牌索引
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_brand_id ON c2c_items(brand_id)')
        
        # 初始化品牌数据
        self.init_brands()
        
        self.conn.commit()

    def init_brands(self):
        """初始化品牌数据"""
        brands = [
            ('TAITO', 'TAITO|タイトー|太东'),
            ('SEGA', 'SEGA|世嘉|セガ'),
            ('BANPRESTO', 'BANPRESTO|万代南梦宫|バンプレスト'),
            ('FURYU', 'FURYU|フリュー|福龙'),
            ('BANDAI', 'BANDAI|万代|バンダイ'),
            ('GOODSMILE', 'GOODSMILE|GSC|굿스마일|グッドスマイル'),
            ('ALTER', 'ALTER|阿尔塔|アルター'),
            ('KOTOBUKIYA', 'KOTOBUKIYA|寿屋|コトブキヤ'),
            ('ANIPLEX', 'ANIPLEX|アニプレックス'),
            ('HOBBY STOCK', 'HOBBY STOCK|ホビーストック'),
            ('KADOKAWA', 'KADOKAWA|角川|カドカワ'),
            ('WAVE', 'WAVE|ウェーブ'),
            ('BROCCOLI', 'BROCCOLI|ブロッコリー'),
            ('AQUAMARINE', 'AQUAMARINE|アクアマリン'),
            ('MEDICOS', 'MEDICOS|メディコス'),
            ('MEGAHOUSE', 'MEGAHOUSE|メガハウス'),
            ('ORANGE ROUGE', 'ORANGE ROUGE|オランジュ・ルージュ'),
            ('STRONGER', 'STRONGER|ストロンガー'),
        ]
        
        for brand_name, keywords in brands:
            self.cursor.execute('''
                INSERT OR IGNORE INTO brands (name, keywords)
                VALUES (?, ?)
            ''', (brand_name, keywords))

    def match_brand(self, item_name):
        """匹配商品品牌"""
        self.cursor.execute('SELECT id, name, keywords FROM brands')
        brands = self.cursor.fetchall()
        
        for brand_id, brand_name, keywords in brands:
            # 将关键词分割成列表
            keyword_list = keywords.split('|')
            # 如果任何一个关键词在商品名称中，返回品牌ID
            if any(keyword.lower() in item_name.lower() for keyword in keyword_list):
                return brand_id
        return None

    def check_item_exists(self, item_id):
        """检查商品是否已存在"""
        self.cursor.execute('SELECT id FROM c2c_items WHERE id = ?', (item_id,))
        return self.cursor.fetchone() is not None

    def fetch_data(self, next_id=None):
        """获取数据"""
        data = {
            "sortType": "TIME_DESC",
            "nextId": next_id if next_id else ""
        }
        
        delay = random.uniform(self.min_sleep, self.max_sleep)
        print(f"等待 {delay:.1f} 秒后发起请求...")
        print(f"请求参数: {json.dumps(data, ensure_ascii=False)}")
        time.sleep(delay)
        
        try:
            response = requests.post(self.url, headers=self.headers, json=data, timeout=10)
            print(f"请求状态码: {response.status_code}")
            
            response_json = response.json()
            if response_json['code'] != 0:
                print("异常响应详情:")
                print(f"URL: {self.url}")
                print(f"Headers: {json.dumps(dict(response.request.headers), ensure_ascii=False, indent=2)}")
                print(f"Request Body: {json.dumps(data, ensure_ascii=False, indent=2)}")
                print(f"Response Body: {json.dumps(response_json, ensure_ascii=False, indent=2)}")
            
            return response_json
            
        except requests.exceptions.RequestException as e:
            print(f"请求异常: {e}")
            print("请求详情:")
            print(f"URL: {self.url}")
            print(f"Headers: {json.dumps(self.headers, ensure_ascii=False, indent=2)}")
            print(f"Request Body: {json.dumps(data, ensure_ascii=False, indent=2)}")
            if hasattr(e.response, 'text'):
                print(f"Response Body: {e.response.text}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析异常: {e}")
            print("响应内容:")
            print(response.text)
            return None

    def save_to_db(self, item):
        """保存数据到数据库"""
        try:
            # 检查是否已存在
            if self.check_item_exists(item['c2cItemsId']):
                return False
            
            # 匹配品牌
            brand_id = self.match_brand(item['c2cItemsName'])
            
            # 处理SKU数据
            for sku in item['detailDtoList']:
                # 先更新SKU主表
                self.cursor.execute('''
                    INSERT OR REPLACE INTO skus (
                        sku_id, name, img, market_price, type
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    sku['skuId'],
                    sku['name'],
                    sku['img'],
                    float(sku['marketPrice']) / 100,  # 转换为元
                    sku['type']
                ))
                
                # 插入或更新商品主表数据
                self.cursor.execute('''
                    INSERT OR REPLACE INTO c2c_items (
                        id, type, name, brand_id, sku_id, items_id,
                        total_items_count, price, show_price, show_market_price,
                        uid, payment_time, is_my_publish, uspace_jump_url,
                        uface, uname
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item['c2cItemsId'],
                    item['type'],
                    item['c2cItemsName'],
                    brand_id,
                    sku['skuId'],
                    sku['itemsId'],
                    item['totalItemsCount'],
                    float(item['price']) / 100,  # 转换为元
                    item['showPrice'],
                    item['showMarketPrice'],
                    item['uid'],
                    item['paymentTime'],
                    1 if item['isMyPublish'] else 0,
                    item['uspaceJumpUrl'],
                    item['uface'],
                    item['uname']
                ))
            
            self.conn.commit()
            return True
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                self.conn.rollback()
                return False
            raise
        except Exception as e:
            print(f"保存数据出错: {e}")
            self.conn.rollback()
            raise

    def run(self, max_pages=100):
        """持续运行爬虫，达到最大页数后从头开始"""
        while True:  # 外层循环，确保持续运行
            next_id = None
            page = 0
            total_items = 0
            new_items_count = 0
            self.duplicate_count = 0  # 重置重复计数
            
            print("\n=== 开始新一轮爬取 ===")
            print(f"计划爬取最大页数: {max_pages}")
            print(f"连续重复数据页数阈值: {self.max_duplicate_pages}")
            
            while page < max_pages and self.duplicate_count < self.max_duplicate_pages:
                try:
                    print(f"\n正在爬取第 {page + 1} 页...")
                    response_data = self.fetch_data(next_id)
                    
                    if not response_data:
                        print("获取数据失败，等待30秒后重试...")
                        time.sleep(self.error_sleep)
                        continue
                    
                    if response_data['code'] != 0:
                        print(f"获取数据失败: {response_data['message']}")
                        print(f"等待{self.error_sleep}秒后重试...")
                        time.sleep(self.error_sleep)
                        continue
                    
                    items = response_data['data']['data']
                    if not items:
                        print("没有更多数据了")
                        break
                    
                    print(f"本页获取到 {len(items)} 个商品")
                    page_new_items = 0
                    
                    for item in items:
                        if self.save_to_db(item):
                            page_new_items += 1
                        total_items += 1
                    
                    # 检查本页新增商品数量
                    if page_new_items == 0:
                        self.duplicate_count += 1
                        print(f"本页没有新商品，连续重复页数: {self.duplicate_count}")
                    else:
                        self.duplicate_count = 0
                        new_items_count += page_new_items
                        print(f"本页新增商品数: {page_new_items}")
                    
                    next_id = response_data['data']['nextId']
                    page += 1
                    
                    print(f"当前进度: {page}/{max_pages} 页")
                    print(f"已爬取商品总数: {total_items}, 新增商品数: {new_items_count}")
                    print(f"连续重复页数: {self.duplicate_count}/{self.max_duplicate_pages}")
                    
                except Exception as e:
                    print(f"爬取过程出错: {e}")
                    import traceback
                    print("详细错误信息:")
                    print(traceback.format_exc())
                    print(f"等待{self.fatal_sleep}秒后继续...")
                    time.sleep(self.fatal_sleep)
                    continue

            # 一轮爬取结束
            if self.duplicate_count >= self.max_duplicate_pages:
                print(f"\n已连续 {self.max_duplicate_pages} 页没有新数据")
            elif page >= max_pages:
                print(f"\n已达到最大页数限制 {max_pages}")
            
            print("\n=== 本轮爬取完成 ===")
            print(f"总计爬取页数: {page}")
            print(f"总计商品数: {total_items}")
            print(f"新增商品数: {new_items_count}")
            print(f"等待{self.error_sleep}秒后开始下一轮爬取...")
            time.sleep(self.error_sleep)

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='B站商城爬虫')
    parser.add_argument('--cookie', type=str, required=True, help='浏览器Cookie字符串')
    parser.add_argument('--pages', type=int, default=100, help='要爬取的最大页数，默认100页')
    parser.add_argument('--duplicate-threshold', type=int, default=5, help='连续重复页数阈值，默认5页')
    parser.add_argument('--min-sleep', type=float, default=2, help='最小休眠时间(秒)，默认2秒')
    parser.add_argument('--max-sleep', type=float, default=5, help='最大休眠时间(秒)，默认5秒')
    parser.add_argument('--error-sleep', type=int, default=30, help='错误重试休眠时间(秒)，默认30秒')
    parser.add_argument('--fatal-sleep', type=int, default=60, help='严重错误休眠时间(秒)，默认60秒')
    args = parser.parse_args()

    spider = BiliMallSpider(cookie=args.cookie)
    spider.max_duplicate_pages = args.duplicate_threshold
    spider.min_sleep = args.min_sleep
    spider.max_sleep = args.max_sleep
    spider.error_sleep = args.error_sleep
    spider.fatal_sleep = args.fatal_sleep
    try:
        spider.run(max_pages=args.pages)
    finally:
        spider.close()
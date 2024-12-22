export interface SkuInfo {
  sku_id: number
  name: string
  img: string
  market_price: number
  price_range: {
    min: number
    max: number
  }
  total_items: number
}

export interface ItemDetail {
  c2c_items_id: number
  seller_name: string
  seller_uid: string
  seller_avatar: string
  seller_url: string
  price: number
  market_price: number
  url: string
} 
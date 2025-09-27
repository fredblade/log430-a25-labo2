"""
Orders (read-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""

from collections import defaultdict
from db import get_sqlalchemy_session, get_redis_conn
from sqlalchemy import desc
from models.order import Order

def get_order_by_id(order_id):
    """Get order by ID from Redis"""
    r = get_redis_conn()
    return r.hgetall(order_id)

def get_orders_from_mysql(limit=9999):
    """Get last X orders"""
    session = get_sqlalchemy_session()
    return session.query(Order).order_by(desc(Order.id)).limit(limit).all()

def get_orders_from_redis(limit=9999):
    """Get last X orders from Redis"""
    r = get_redis_conn()
    
    order_keys = r.keys("order:*")
    order_keys = [key for key in order_keys if ":item:" not in key]
    
    orders = []
    for key in order_keys:
        order_data = r.hgetall(key)
        if order_data and 'id' in order_data:
            order = Order(
                user_id=int(order_data['user_id']),
                total_amount=float(order_data['total_amount'])
            )
            order.id = int(order_data['id'])
            orders.append(order)
    
    # Triage
    orders.sort(key=lambda a: a.id, reverse=True)
    
    return orders[:limit]

def get_highest_spending_users():
    """Get report of best selling products"""
    orders = get_orders_from_redis()
    expenses_by_user = defaultdict(float)
    for order in orders:
        # note: pour l'etape no.5, le bout de code order.total est changer a order.total_amount
        expenses_by_user[order.user_id] += order.total_amount
    highest_spending_users = sorted(expenses_by_user.items(), key=lambda item: item[1], reverse=True)
    
    return highest_spending_users[:10]

def get_best_selling_products():
    """Get list of best selling products from Redis"""
    r = get_redis_conn()
    
    product_keys = r.keys("product_sold:*")
    
    products_sold = []
    for key in product_keys:
        product_id = int(key.split(':')[1])
        quantity_sold = int(r.get(key) or 0)
        products_sold.append((product_id, quantity_sold))

    best_selling = sorted(products_sold, key=lambda item: item[1], reverse=True)
    
    return best_selling
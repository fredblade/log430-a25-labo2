"""
Orders (write-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
from models.product import Product
from models.order_item import OrderItem
from models.order import Order
from queries.read_order import get_orders_from_mysql
from db import get_sqlalchemy_session, get_redis_conn

def add_order(user_id: int, items: list):
    """Insert order with items in MySQL, keep Redis in sync"""
    if not user_id or not items:
        raise ValueError("Vous devez indiquer au moins 1 utilisateur et 1 item pour chaque commande.")

    try:
        product_ids = []
        for item in items:
            product_ids.append(int(item['product_id']))
    except Exception as e:
        print(e)
        raise ValueError(f"L'ID Article n'est pas valide: {item['product_id']}")
    session = get_sqlalchemy_session()

    try:
        products_query = session.query(Product).filter(Product.id.in_(product_ids)).all()
        price_map = {product.id: product.price for product in products_query}
        total_amount = 0
        order_items_data = []
        
        for item in items:
            pid = int(item["product_id"])
            qty = float(item["quantity"])

            if not qty or qty <= 0:
                raise ValueError(f"Vous devez indiquer une quantité superieure à zéro.")

            if pid not in price_map:
                raise ValueError(f"Article ID {pid} n'est pas dans la base de données.")

            unit_price = price_map[pid]
            total_amount += unit_price * qty
            order_items_data.append({
                'product_id': pid,
                'quantity': qty,
                'unit_price': unit_price
            })
        
        new_order = Order(user_id=user_id, total_amount=total_amount)
        session.add(new_order)
        session.flush() 
        
        order_id = new_order.id

        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order_id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price']
            )
            session.add(order_item)

        session.commit()

        add_order_to_redis(order_id, user_id, total_amount, items)

        return order_id

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def delete_order(order_id: int):
    """Delete order in MySQL, keep Redis in sync"""
    session = get_sqlalchemy_session()
    try:
        order = session.query(Order).filter(Order.id == order_id).first()
        
        if order:
            session.delete(order)
            session.commit()

            delete_order_from_redis(order_id)
            return 1  
        else:
            return 0  
            
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def add_order_to_redis(order_id, user_id, total_amount, items):
    """Insert order to Redis"""
    r = get_redis_conn()
    
    # commande principal avec hash
    order_key = f"order:{order_id}"
    r.hset(order_key, mapping={
        "id": order_id,
        "user_id": user_id,
        "total_amount": total_amount
    })
    
    # items de la commande
    for item in items:
        item_key = f"order:{order_id}:item:{item['product_id']}"
        r.hset(item_key, mapping={
            "product_id": item['product_id'],
            "quantity": item['quantity']
        })
        
        # Incrementer le compteur des produits vendus
        product_sold_key = f"product_sold:{item['product_id']}"
        r.incr(product_sold_key, int(item['quantity']))

def delete_order_from_redis(order_id):
    """Delete order from Redis"""
    r = get_redis_conn()
    
    # Decrementer les compteurs des produits vendus avant suppression
    item_keys = r.keys(f"order:{order_id}:item:*")
    for item_key in item_keys:
        item_data = r.hgetall(item_key)
        if item_data and 'product_id' in item_data and 'quantity' in item_data:
            product_sold_key = f"product_sold:{item_data['product_id']}"
            r.decr(product_sold_key, int(item_data['quantity']))
    
    # commande principale
    order_key = f"order:{order_id}"
    r.delete(order_key)
    
    # items de la commande
    if item_keys:
        r.delete(*item_keys)

def sync_all_orders_to_redis():
    """ Sync orders from MySQL to Redis """
    
    rows_added = 0
    try:
        orders_from_mysql = get_orders_from_mysql()
        
        session = get_sqlalchemy_session()
        try:
            for order in orders_from_mysql:
                # Recuperer les items
                order_items_query = session.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                
                # Convertir les donnees
                items = []
                for item in order_items_query:
                    items.append({
                        'product_id': item.product_id,
                        'quantity': item.quantity
                    })
                
                add_order_to_redis(order.id, order.user_id, order.total_amount, items)
                rows_added += 1
            
        finally:
            session.close()
            
    except Exception as e:
        print(e)
        return 0
    
    return rows_added
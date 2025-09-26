"""
Report view
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
from views.template_view import get_template, get_param
from queries.read_order import get_highest_spending_users, get_best_selling_products
from queries.read_user import get_user_by_id
from queries.read_product import get_product_by_id

def show_highest_spending_users():
    """ Show report of highest spending users """
    highest_spenders = get_highest_spending_users()
    
    # Construire la liste HTML
    list_items = ""
    for user_id, total_spent in highest_spenders:
        user_info = get_user_by_id(user_id)
        user_name = user_info.get('name', f'Utilisateur {user_id}')
        user_email = user_info.get('email', 'N/A')
        
        list_items += f"""
            <li>
                <strong>{user_name}</strong> ({user_email}) - {total_spent:.2f}$
            </li>
        """
    
    content = f"""
        <h2>Les plus gros acheteurs</h2>
        <ul>
            {list_items}
        </ul>
    """
    
    return get_template(content)

def show_best_sellers():
    """ Show report of best selling products """
    best_sellers = get_best_selling_products()
    
    # Construire la liste HTML
    list_items = ""
    for product_id, quantity_sold in best_sellers:
        product_info = get_product_by_id(product_id)
        product_name = product_info.get('name', f'Produit {product_id}')
        product_sku = product_info.get('sku', 'N/A')
        
        list_items += f"""
            <li>
                <strong>{product_name}</strong> (SKU: {product_sku}) - {quantity_sold} vendus
            </li>
        """
    
    content = f"""
        <h2>Les articles les plus vendus</h2>
        <ul>
            {list_items}
        </ul>
    """
    
    return get_template(content)
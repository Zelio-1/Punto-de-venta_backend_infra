from flask import Blueprint, request, jsonify
from config.db import db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
from decimal import Decimal, InvalidOperation

#Creating the blueprint 
sales_bp = Blueprint('sales', __name__)

#Defining a endpoint to create a sale (POST method)
@sales_bp.route('/sales', methods = ['POST'])
@jwt_required()
def create_sale():
    
    current_user = get_jwt_identity()

    data = request.get_json()

    products = data.get('products')
    quantity = data.get('quantity')
    
    connection = db_connection()
    cursor = connection.cursor()
    
    user_confirmation = 'select id_user from usuarios where id_user = %s'
    cursor.execute(user_confirmation, (current_user, ))
    usuario = cursor.fetchone()
    
    if not usuario[0] == int(current_user): 
        cursor.close()
        return jsonify({"Message":"Invalid credentials"})

    #Checking if any of the products exist
    cursor.execute('select*from productos_inexistentes(%s)', (products, )) 

    products_confirmation = cursor.fetchall()

    if products_confirmation: 
        cursor.close()
        return jsonify({"The product(s) does not exist.":products_confirmation})
    
    cursor.execute('select*from productos_sin_stock (%s)', (products, ))

    stock_confirmation = cursor.fetchall()

    if stock_confirmation: 
        return jsonify ({"Empty stock:":stock_confirmation})
    
    cursor.execute('select*from obtener_precios_desde_productos(%s)', (products, ))
    unit_price = cursor.fetchall()
    total = 0
    print(products)
    for i in range(len(unit_price)): 
        price = float(unit_price[i][1])
        total += price*float(quantity[i])
    
    cursor.execute('select ticket_id from ventas where ticket_id = (select max(ticket_id) from ventas)')
    last_ticket_id = cursor.fetchone()

    if last_ticket_id is None: 
        last_ticket_id = 1
        ticket_number = 'TCK-'+ str(last_ticket_id)
        ticket_id = last_ticket_id
    else:
        ticket_number = 'TCK-'+ str(last_ticket_id[0] + 1)
        ticket_id = last_ticket_id[0] + 1

    cursor.execute('select localtimestamp;')
    sale_datetime = cursor.fetchone()

    sale_state = 'Procesada'

    try: 
        query_3 = 'INSERT INTO ventas (ticket_id, quantity, unit_price, total, id_user, ticket_number, sale_datetime, sale_state, products) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)'
        cursor.execute(query_3, (ticket_id, quantity, unit_price, total, current_user, ticket_number, sale_datetime, sale_state, products))
        cursor.connection.commit()
        return jsonify({"Message":"sale completed"})
    except Exception as error: 
        return jsonify({"Error":f"There was an error during the sale creation: {str(error)}"})
    finally: 
        cursor.close()

#Defining a endpoint to list the sales of an employee (GET method)
@sales_bp.route('/sales', methods = ['GET'])
@jwt_required()
def get_all_sales(): 

    current_user = get_jwt_identity()
    
    connection = db_connection()
    cursor = connection.cursor()
    
    cursor.execute('select role from usuarios where id_user = %s;', (current_user, ))
    admin = cursor.fetchone()
    if admin[0] != 'admin': 
        user_confirmation = 'select id_user from ventas where id_user = %s'
        cursor.execute(user_confirmation, (current_user, ))
        usuario = cursor.fetchone()
        
        if not usuario[0] == int(current_user): 
            cursor.close()
            return jsonify({"Message":"Invalid credentials"})

        query_2 = 'select *from ventas where id_user = %s'
        cursor.execute(query_2, (current_user, )) 
        user_sales = cursor.fetchall()

        cursor.close()

        if not user_sales: 
            return jsonify ({"Error":"The user does not have sales yet"})
        else: 
            return jsonify ({"User's sales":user_sales}), 200
    else: 
        cursor.execute('select*from ventas;') 
        all_sales = cursor.fetchall()

        cursor.close()

        if not all_sales: 
            return jsonify ({"Error":"Theres no sales to show yet"})
        else: 
            return jsonify ({"Total sales":all_sales}), 200
    
#Retrieving a specific sale done by a user
@sales_bp.route('/sales/<int:id_sale>', methods = ['GET'])
@jwt_required()
def get_one_sale(id_sale): 

    current_user = get_jwt_identity()

    connection = db_connection()
    cursor = connection.cursor()

    cursor.execute('select role from usuarios where id_user = %s;', (current_user, ))
    admin = cursor.fetchone()
    if admin[0] != 'admin': 
        user_confirmation = 'select id_user from ventas where id_sale = %s;'
        cursor.execute(user_confirmation, (id_sale, ))
        usuario = cursor.fetchone()
        
        if not usuario[0] == int(current_user): 
            cursor.close()
            return jsonify({"Message":"Invalid credentials"})
 
    cursor.execute('select*from ventas where id_sale = %s', (id_sale, ))
    sale = cursor.fetchone()
    cursor.close()
    if not sale: 
        return jsonify ({"Message:":f"That sale with the id_sale: {id_sale}, does not exist"}), 404
    else:
        return jsonify({"Sale": sale}), 200

#Cancel a specific sale done by a user
@sales_bp.route('/sales/<int:id_sale>/cancel', methods = ['PUT'])
@jwt_required()
def cancel_one_sale(id_sale): 

    current_user = get_jwt_identity()

    connection = db_connection()
    cursor = connection.cursor()

    cursor.execute('select role from usuarios where id_user = %s;', (current_user, ))
    admin = cursor.fetchone()
    if admin[0] != 'admin': 
        user_confirmation = 'select id_user from ventas where id_sale = %s;'
        cursor.execute(user_confirmation, (id_sale, ))
        usuario = cursor.fetchone()
        
        if not usuario[0] == int(current_user): 
            cursor.close()
            return jsonify({"Message":"Invalid credentials"})


    cursor.execute ('select sale_state from ventas where id_sale = %s', (id_sale, ))
    already_canceled = cursor.fetchone()

    if already_canceled[0] == 'Cancelada':
        cursor.close()
        return jsonify({"Message:":"That sale has already been canceled."})

    sale_status = 'Cancelada'

    cursor.execute('update ventas set sale_state = %s where id_sale = %s;', (sale_status, id_sale))
    cursor.connection.commit()

    cursor.execute('select sale_state from ventas where id_sale = %s', (id_sale, ))
    sale = cursor.fetchone()
    cursor.close()
    if not sale: 
        return jsonify ({"Message:":f"Error when canceling the sale with id_sale: {id_sale}"})
    else:
        return jsonify({"Message": "sale successfully canceled"}), 200

#Delete a specific sale done by the administrators only
@sales_bp.route('/sales/delete/<int:id_sale>', methods = ['DELETE'])
@jwt_required()
def delete_sale(id_sale): 

    current_user = get_jwt_identity()

    connection = db_connection()
    cursor = connection.cursor()

    user_confirmation = 'select role from usuarios where id_user = %s;'
    cursor.execute(user_confirmation, (current_user, ))
    usuario = cursor.fetchone()
    
    if usuario[0] != 'admin': 
        cursor.close()
        return jsonify({"Message":"you're not authorized to perform this operation"})

    cursor.execute ('select*from ventas where id_sale = %s', (id_sale, ))
    already_canceled = cursor.fetchone()

    if not already_canceled[0]:
        cursor.close()
        return jsonify({"Message:":"That sale has already been deleted"})

    cursor.execute('delete from ventas where id_sale = %s', (id_sale, ))
    cursor.connection.commit()

    cursor.execute('select*from ventas where id_sale = %s', (id_sale, ))
    sale = cursor.fetchone()
    cursor.close()
    if not sale: 
        return jsonify ({"Message:":f"sale successfully deleted"}), 200
    else:
        return jsonify({"Message": "Error deleting sale"})

# GET /sales/<ticket_id>/receipt
@sales_bp.route('/sales/<int:ticket_id>/receipt', methods=['GET'])
@jwt_required()
def get_receipt(ticket_id):
    """
    Recibo desde 'ventas' (1 fila por ticket).
    Acceso:
      - admin/manager: cualquier ticket
      - cashier: solo tickets cuyo ventas.id_user == current_user_id
    """
    current_user_id = get_jwt_identity()
    connection = db_connection()
    cursor = connection.cursor()
    try:
        # 1) Rol del usuario actual
        cursor.execute("SELECT role FROM usuarios WHERE id_user = %s AND active = TRUE", (current_user_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Token inválido o usuario no encontrado"}), 401
        role_actual = (row[0] or "").lower()
        if role_actual not in ("admin", "manager", "cashier"):
            return jsonify({"error": "Usuario no autorizado"}), 403

        # 2) Obtener la fila de ventas del ticket (aquí también sabemos el dueño id_user)
        cursor.execute("""
            SELECT
                ticket_id,
                ticket_number,
                sale_datetime,
                sale_state,
                id_user,        -- dueño/cajero que registró la venta
                products,       -- text (posible JSON)
                quantity,       -- text
                unit_price,     -- text
                total           -- numeric(10,2)
            FROM ventas
            WHERE ticket_id = %s
        """, (ticket_id,))
        v = cursor.fetchone()
        if not v:
            return jsonify({"error": "Ticket no encontrado"}), 404

        (_ticket_id, ticket_number, sale_datetime, sale_state, sale_user_id,
         products_text, quantity_text, unit_price_text, total_numeric) = v

        # 3) Si es cashier, sólo puede ver sus propios tickets
        if role_actual == "cashier" and int(sale_user_id) != int(current_user_id):
            return jsonify({"error": "No tienes permiso para ver este recibo"}), 403

        # ---------- armado del recibo ----------
        def to_decimal(x):
            try: return Decimal(str(x))
            except (InvalidOperation, TypeError, ValueError): return Decimal("0")

        def to_int(x):
            try: return int(Decimal(str(x)))
            except (InvalidOperation, TypeError, ValueError): return 0

        items = []
        subtotal = Decimal("0")
        parsed_ok = False

        # 4) Si 'products' trae JSON (lista de líneas), úsalo
        if products_text:
            try:
                data = json.loads(products_text)
                if isinstance(data, list) and data:
                    for it in data:
                        pid = it.get("product_id") or it.get("id_product") or it.get("id") or None
                        pname = it.get("product_name") or it.get("name") or ""
                        up = to_decimal(it.get("unit_price"))
                        qty = to_int(it.get("quantity"))
                        line_total = (up * qty).quantize(Decimal("0.01"))
                        items.append({
                            "product_id": int(pid) if isinstance(pid, (int, float, str)) and str(pid).isdigit() else None,
                            "product_name": pname,
                            "unit_price": float(up),
                            "quantity": qty,
                            "line_total": float(line_total)
                        })
                        subtotal += line_total
                    parsed_ok = True
            except json.JSONDecodeError:
                parsed_ok = False

        # 5) Si no hay JSON válido, usa unit_price * quantity de la fila
        if not parsed_ok:
            up = to_decimal(unit_price_text)
            qty = to_int(quantity_text)
            line_total = (up * qty).quantize(Decimal("0.01"))
            items.append({
                "product_id": None,
                "product_name": "",
                "unit_price": float(up),
                "quantity": qty,
                "line_total": float(line_total)
            })
            subtotal += line_total

        taxes = Decimal("0.00")  # ajusta si manejas impuestos
        total_calc = (subtotal + taxes).quantize(Decimal("0.01"))
        total_db = Decimal(total_numeric or 0).quantize(Decimal("0.01"))

        return jsonify({
            "ticket_id": int(_ticket_id),
            "ticket_number": ticket_number,
            "sale_datetime": str(sale_datetime) if sale_datetime else None,
            "sale_state": sale_state,
            "cashier_user_id": int(sale_user_id) if sale_user_id is not None else None,
            "items": items,
            "summary": {
                "subtotal": float(subtotal.quantize(Decimal("0.01"))),
                "taxes": float(taxes),
                "total_calculated": float(total_calc),
                "total_db": float(total_db)
            }
        }), 200

    except Exception as e:
        return jsonify({"error": f"Ocurrió un error al consultar el recibo: {str(e)}"}), 500
    finally:
        try:
            cursor.close()
            connection.close()
        except:
            pass

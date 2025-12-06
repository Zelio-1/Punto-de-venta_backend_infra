from flask import Blueprint, jsonify, request
from config.db import db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import uuid

productos_bp = Blueprint('productos', __name__)

# ---------------- Helper functions ----------------
def validar_campos_requeridos(data, campos):
    faltantes = [campo for campo in campos if not data.get(campo)]
    if faltantes: 
        return False, f"Please provide the following missing fields: {', '.join(faltantes)}"
    return True, None

def _obtener_rol_activo(cursor, user_id):
    cursor.execute(
        "SELECT role FROM usuarios WHERE id_user = %s AND active = TRUE",
        (user_id,)
    )
    row = cursor.fetchone()
    return (row[0] or "").lower() if row else None

def _autorizar_roles(rol_actual, roles_permitidos):
    return rol_actual in roles_permitidos


# ---------------- Endpoints ----------------

@productos_bp.route('/mostrar', methods=['GET'])
@jwt_required()
def obtener_productos():
    current_user_id = get_jwt_identity()
    connection = db_connection()
    cursor = connection.cursor()
    try:
        rol_actual = _obtener_rol_activo(cursor, current_user_id)
        if not rol_actual:
            return jsonify({"error": "Invalid token or user not found"}), 401
        if not _autorizar_roles(rol_actual, {"admin", "manager", "cashier"}):
            return jsonify({"error": "Unauthorized user (only admin/manager/cashier allowed)"}), 403

        cursor.execute("SELECT * FROM productos;")
        productos = cursor.fetchall()
        if not productos:
            return jsonify({"error": "No products found"}), 404
        return jsonify({"products": productos}), 200
    except Exception as e:
        return jsonify({"error": f"Error in obtener_productos: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()


@productos_bp.route('/<int:id_product>', methods=['GET'])
@jwt_required()
def mostrar_un_producto(id_product):
    current_user_id = get_jwt_identity()
    connection = db_connection()
    cursor = connection.cursor()
    try:
        rol_actual = _obtener_rol_activo(cursor, current_user_id)
        if not rol_actual:
            return jsonify({"error": "Invalid token or user not found"}), 401
        if not _autorizar_roles(rol_actual, {"admin", "manager", "cashier"}):
            return jsonify({"error": "Unauthorized user (only admin/manager/cashier allowed)"}), 403

        cursor.execute("SELECT * FROM productos WHERE id_product = %s", (id_product,))
        producto = cursor.fetchone()
        if not producto:
            return jsonify({"error": "No product with that ID"}), 404
        return jsonify({"product": producto}), 200
    except Exception as error:
        return jsonify({"error": f"Registered error: {str(error)}"}), 500
    finally:
        cursor.close()
        connection.close()


@productos_bp.route('/barcode/<string:barcode>', methods=['GET'])
@jwt_required()
def mostrar_con_barcode(barcode):
    current_user_id = get_jwt_identity()
    connection = db_connection()
    cursor = connection.cursor()
    try:
        rol_actual = _obtener_rol_activo(cursor, current_user_id)
        if not rol_actual:
            return jsonify({"error": "Invalid token or user not found"}), 401
        if not _autorizar_roles(rol_actual, {"admin", "manager", "cashier"}):
            return jsonify({"error": "Unauthorized user (only admin/manager/cashier allowed)"}), 403

        cursor.execute("SELECT * FROM productos WHERE barcode = %s", (barcode,))
        producto = cursor.fetchone()
        if not producto:
            return jsonify({"error": "No product with that barcode"}), 404
        return jsonify({"product": producto}), 200
    except Exception as error:
        return jsonify({"error": f"Registered error: {str(error)}"}), 500
    finally:
        cursor.close()
        connection.close()


@productos_bp.route('/<int:id_product>', methods=['PATCH'])
@jwt_required()
def editar_producto(id_product):
    current_user_id = get_jwt_identity()
    data = request.get_json() or {}
    product_name = data.get("product_name")
    price = data.get("price")
    barcode = data.get("barcode")
    stock = data.get("stock")

    connection = db_connection()
    cursor = connection.cursor()
    try:
        rol_actual = _obtener_rol_activo(cursor, current_user_id)
        if not rol_actual:
            return jsonify({"error": "Invalid token or user not found"}), 401
        if not _autorizar_roles(rol_actual, {"admin", "manager"}):
            return jsonify({"error": "Unauthorized user (only admin/manager allowed)"}), 403

        cursor.execute("SELECT 1 FROM productos WHERE id_product = %s", (id_product,))
        existe = cursor.fetchone()
        if not existe:
            return jsonify({"error": "No product with that ID"}), 404

        campos = []
        valores = []
        if product_name is not None:
            campos.append("product_name = %s")
            valores.append(product_name)
        if price is not None:
            campos.append("price = %s")
            valores.append(price)
        if barcode is not None:
            campos.append("barcode = %s")
            valores.append(barcode)
        if stock is not None:
            campos.append("stock = %s")
            valores.append(stock)

        if not campos:
            return jsonify({"error": "No fields to update"}), 400

        valores.append(id_product)
        query_update = f"UPDATE productos SET {', '.join(campos)} WHERE id_product = %s"
        cursor.execute(query_update, tuple(valores))
        connection.commit()

        return jsonify({"message": f"Product {id_product} updated successfully"}), 200
    except Exception as error:
        return jsonify({"error": f"Registered error: {str(error)}"}), 500
    finally:
        cursor.close()
        connection.close()


@productos_bp.route('/agregar', methods=['POST'])
@jwt_required()
def Agregar_Productos():
    current_user_id = get_jwt_identity()
    data = request.get_json() or {}

    connection = db_connection()
    cursor = connection.cursor()
    try:
        rol_actual = _obtener_rol_activo(cursor, current_user_id)
        if not rol_actual:
            return jsonify({"error": "Invalid token or user not found"}), 401
        if not _autorizar_roles(rol_actual, {"admin", "manager"}):
            return jsonify({"error": "Unauthorized user (only admin/manager allowed)"}), 403

        campos_requeridos = ["product_name", "price", "barcode", "stock"]
        valido, mensaje = validar_campos_requeridos(data, campos_requeridos)
        if not valido:
            return jsonify({"error": mensaje}), 400

        product_name = data.get("product_name")
        price = data.get("price")
        barcode = data.get("barcode")
        stock = data.get("stock")

        cursor.execute("SELECT 1 FROM productos WHERE product_name = %s", (product_name,))
        existing_product = cursor.fetchone()
        if existing_product:
            return jsonify({"error": "Product with that name already exists"}), 400

        cursor.execute(
            "INSERT INTO productos (product_name, price, barcode, stock) VALUES (%s, %s, %s, %s)",
            (product_name, price, barcode, stock)
        )
        connection.commit()
        return jsonify({"message": f"Product {product_name} created successfully"}), 201
    except Exception as error:
        return jsonify({"error": f"Registered error: {str(error)}"}), 500
    finally:
        cursor.close()
        connection.close()

UPLOAD_FOLDER = 'static/productos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Crear directorio si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Verifica si el archivo es una imagen válida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Endpoints para las imagenes

@productos_bp.route('/crear/imagen', methods=['POST'])
@jwt_required()
def subir_imagen_producto_crear():
    try:
        # Verificar que venga la imagen
        if 'imagen' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No se envió ninguna imagen'
            }), 400

        file = request.files['imagen']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nombre de archivo vacío'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Tipo de archivo no permitido. Use: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # Aquí se podría crear el producto si se necesitan datos adicionales
        # Por simplicidad asumimos que el producto ya se creó y solo asociamos imagen
        # Si quieres, puedes recibir datos JSON en paralelo y crear el producto aquí

        # Generar nombre único para la imagen
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        full_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(full_path)

        # Guardar URL para la base de datos
        imagen_url = f"/static/productos/{filename}"

        # Insertar registro en DB o actualizar el último producto creado
        conn = db_connection()
        cur = conn.cursor()

        # Obtener el último producto creado (más reciente)
        cur.execute('SELECT id_product, imagen_url FROM productos ORDER BY created_at DESC LIMIT 1')
        producto = cur.fetchone()

        if not producto:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'No se encontró un producto para asociar la imagen'
            }), 404

        # Eliminar imagen anterior si existe
        if producto[1]:
            old_full = producto[1].replace('/static/', 'static/')
            if os.path.exists(old_full):
                try:
                    os.remove(old_full)
                except:
                    pass

        # Actualizar la DB con la nueva imagen
        cur.execute(
            'UPDATE productos SET imagen_url = %s WHERE id_product = %s',
            (imagen_url, producto[0])
        )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'mensaje': 'Imagen subida exitosamente',
            'imagen_url': request.host_url.rstrip('/') + imagen_url
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@productos_bp.route('/<int:producto_id>/imagen', methods=['PATCH'])
@jwt_required()
def subir_imagen_producto(producto_id):
    
    if 'imagen' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No se envió ninguna imagen'
        }), 400
    
    file = request.files['imagen']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'Nombre de archivo vacío'
        }), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'error': f'Tipo de archivo no permitido. Use: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    try:
        # Verificar que el producto existe
        conn = db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id_product, imagen_url FROM productos WHERE id_product = %s', (producto_id,))
        producto = cur.fetchone()
        
        if not producto:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Producto no encontrado'
            }), 404
        
        # Generar nombre único para el archivo
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        
        # Ruta completa
        full_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Guardar imagen
        file.save(full_path)
        
        # URL para la base de datos
        imagen_url = f"/static/productos/{filename}"
        
        # Eliminar imagen anterior si existe
        if producto[1]:
            old_full = producto[1].replace('/static/', 'static/')
            if os.path.exists(old_full):
                try:
                    os.remove(old_full)
                except:
                    pass
        
        # Actualizar base de datos (sin thumbnail)
        cur.execute(
            'UPDATE productos SET imagen_url = %s WHERE id_product = %s',
            (imagen_url, producto_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'mensaje': 'Imagen subida exitosamente',
            'imagen_url': request.host_url.rstrip('/') + imagen_url
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@productos_bp.route('/<int:producto_id>/imagen', methods=['DELETE'])
@jwt_required()
def eliminar_imagen_producto(producto_id):
    """Eliminar imagen de un producto"""
    try:
        conn = db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT imagen_url FROM productos WHERE id_product = %s', (producto_id,))
        producto = cur.fetchone()
        
        if not producto:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Producto no encontrado'
            }), 404
        
        # Eliminar archivo del sistema
        if producto[0]:
            full_path = producto[0].replace('/static/', 'static/')
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except:
                    pass
        
        # Actualizar base de datos
        cur.execute(
            'UPDATE productos SET imagen_url = NULL WHERE id_product = %s',
            (producto_id,)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'mensaje': 'Imagen eliminada exitosamente'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@productos_bp.route('/<int:producto_id>/product_state', methods=['PATCH'])
@jwt_required()
def cambiar_estado_producto(producto_id): 
    current_user = get_jwt_identity()
    data = request.get_json() or request.form.to_dict()
    nuevo_estado = data.get("product_state")

    # Validar que venga el estado
    if not nuevo_estado or nuevo_estado not in {"Enable", "Disable"}:
        return jsonify({"error": "El campo 'state' es requerido y debe ser 'Enable' o 'Disable'"}), 400

    connection = db_connection()
    cursor = connection.cursor()
    try:
        # Verificar rol
        rol_actual = _obtener_rol_activo(cursor, current_user)
        if not rol_actual:
            return jsonify({"error": "Invalid token or user not found"}), 401
        if not _autorizar_roles(rol_actual, {"admin", "manager"}):
            return jsonify({"error": "Unauthorized user (only admin/manager allowed)"}), 403

        # Verificar si el producto existe
        cursor.execute("SELECT product_state FROM productos WHERE id_product = %s", (producto_id,))
        producto = cursor.fetchone()
        if not producto:
            return jsonify({"error": "No product with that ID"}), 404

        # Actualizar el estado
        cursor.execute(
            "UPDATE productos SET product_state = %s WHERE id_product = %s",
            (nuevo_estado, producto_id)
        )
        connection.commit()

        return jsonify({
            "message": f"Product {producto_id} state updated successfully",
            "new_state": nuevo_estado
        }), 200

    except Exception as error:
        connection.rollback()
        return jsonify({"error": f"Registered error: {str(error)}"}), 500
    finally:
        cursor.close()
        connection.close()
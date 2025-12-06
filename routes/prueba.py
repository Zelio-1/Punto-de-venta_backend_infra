from flask import Blueprint, jsonify
from config.db import db_connection

productos_bp = Blueprint('productos', __name__)

@productos_bp.route('/productos', methods=['GET'])
def obtener_productos():
    connection = db_connection()
    cursor = connection.cursor()
    query = "SELECT * FROM Productos;"
    cursor.execute(query)
    productos = cursor.fetchall()
    cursor.close()
    connection.close()
    if not productos:
        return jsonify({"error": "No hay productos registrados"}), 404
    else:
        return jsonify({"productos": productos}), 200
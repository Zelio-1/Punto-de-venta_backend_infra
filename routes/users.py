from flask import Blueprint, jsonify, request
from config.db import db_connection
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
import datetime

users_bp = Blueprint('users', __name__)
bcrypt = Bcrypt()

ROLES_PERMITIDOS = {'admin', 'cashier', 'manager'}

def validar_campos_requeridos(data, campos):
    faltantes = [campo for campo in campos if not data.get(campo)]
    if faltantes:
        return False, f"Fill in the missing fields: {', '.join(faltantes)}"
    return True, None

# Registro de usuarios
@users_bp.route('/signIn', methods=['POST'])
@jwt_required()  # paréntesis por consistencia con flask-jwt-extended v4+
def registrar_usuario():
    # identidad del JWT (id del usuario autenticado)
    current_user_id = get_jwt_identity()

    data = request.get_json() or {}
    # Validaciones de payload
    valido, mensaje = validar_campos_requeridos(data, ["username", "password", "role"])
    if not valido:
        return jsonify({"error": mensaje}), 400

    username = data.get("username", "").strip()
    password = data.get("password")
    role = (data.get("role") or "").strip().lower()

    if role not in ROLES_PERMITIDOS:
        return jsonify({"error": f"Invalid role. Use: {', '.join(sorted(ROLES_PERMITIDOS))}"}), 400

    connection = db_connection()
    if not connection:
        return jsonify({"error": "Couldnt connect to DB"}), 500

    cursor = None
    try:
        cursor = connection.cursor()

        # 1) Verificar que el usuario del token exista y sea ADMIN
        cursor.execute(
            "SELECT role FROM usuarios WHERE id_user = %s AND active = TRUE",
            (current_user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Invalid token or user not found"}), 401

        role_actual = (row[0] or "").lower()
        if role_actual != "admin":
            return jsonify({"error": "Unathorized user (only admin)"}), 403

        # 2) Verificar que no exista ya ese username
        cursor.execute("SELECT 1 FROM usuarios WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({"error": "Username already exists"}), 400

        # 3) Insertar usuario nuevo
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (%s, %s, %s)",
            (username, hashed_password, role)
        )
        connection.commit()
        return jsonify({"mensaje": f"User {username} [{role}] created"}), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"error": f"Error while creating user: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        connection.close()


# Login
@users_bp.route('/logIn', methods=['POST'])
def login():
    data = request.get_json() or {}

    valido, mensaje = validar_campos_requeridos(data, ["username", "password"])
    if not valido:
        return jsonify({"error": mensaje}), 400

    username = data.get("username").strip()
    password = data.get("password")

    connection = db_connection()
    if not connection:
        return jsonify({"error": "Couldnt connect to DB"}), 500

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT password, id_user FROM usuarios WHERE username = %s",
            (username,)
        )
        row = cursor.fetchone()  # row = (hashed_pwd, id_user) o None

        if row and bcrypt.check_password_hash(row[0], password):
            expires = datetime.timedelta(minutes=60)
            access_token = create_access_token(identity=str(row[1]), expires_delta=expires)
            return jsonify({"accessToken": access_token}), 200

        return jsonify({"error": "Incorrect credencials"}), 401

    except Exception as e:
        return jsonify({"error": f"Error while trying to login: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        connection.close()

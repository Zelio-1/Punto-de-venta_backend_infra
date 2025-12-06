from flask import Blueprint, jsonify
from config.db import db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports/sales-summary', methods=['GET'])
@jwt_required()
def sales_summary():
    current_user_id = get_jwt_identity()
    connection = db_connection()
    cursor = connection.cursor()
    try:
        # Validar rol
        cursor.execute("SELECT role FROM usuarios WHERE id_user = %s AND active = TRUE", (current_user_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Invalid token or user not found"}), 401
        role_actual = (row[0] or "").lower()
        if role_actual not in ("admin", "manager"):
            return jsonify({"error": "Unathorized user (only admin/manager)"}), 403

        #Usa 'total' (NUMERIC) en lugar de unit_price * quantity
        cursor.execute("""
            SELECT 
                COALESCE(SUM(v.total), 0) AS total_amount,
                COUNT(DISTINCT v.ticket_id) AS tickets
            FROM ventas v;
        """)
        total_amount, tickets = cursor.fetchone()
        total_amount = float(total_amount or 0)
        tickets = int(tickets or 0)
        avg_ticket = round(total_amount / tickets, 2) if tickets > 0 else 0.0

        return jsonify({
            "total_amount": total_amount,
            "tickets": tickets,
            "avg_ticket": avg_ticket
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error in sales-summary: {str(e)}"}), 500
    finally:
        try:
            cursor.close()
            connection.close()
        except:
            pass


@reports_bp.route('/reports/sales-employee', methods=['GET'])
@jwt_required()
def sales_employee():
    current_user_id = get_jwt_identity()
    connection = db_connection()
    cursor = connection.cursor()
    try:
        # Validar rol
        cursor.execute("SELECT role FROM usuarios WHERE id_user = %s AND active = TRUE", (current_user_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Invalid token or user not found"}), 401
        role_actual = (row[0] or "").lower()
        if role_actual not in ("admin", "manager"):
            return jsonify({"error": "Unathorized user (only admin/manager)"}), 403

        #Usa 'total' para importes; castea quantity sólo si es numérica (regex)
        cursor.execute("""
            SELECT 
                v.id_user,
                COUNT(DISTINCT v.ticket_id) AS tickets,
                COALESCE(SUM(v.total), 0) AS total_amount,
                COALESCE(SUM(
                    CASE 
                        WHEN v.quantity ~ '^[0-9]+(\\.[0-9]+)?$' THEN v.quantity::numeric
                        ELSE 0
                    END
                ), 0) AS total_units
            FROM ventas v
            GROUP BY v.id_user
            ORDER BY total_amount DESC;
        """)
        rows = cursor.fetchall()

        result = [{
            "id_user": int(r[0]) if r[0] is not None else None,
            "tickets": int(r[1] or 0),
            "total_amount": float(r[2] or 0),
            "total_units": float(r[3] or 0)  # puede ser fraccional si quantity trae decimales
        } for r in rows]

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Error in sales-employee: {str(e)}"}), 500
    finally:
        try:
            cursor.close()
            connection.close()
        except:
            pass

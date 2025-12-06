from flask import Flask, send_from_directory, jsonify
from flask_jwt_extended import JWTManager
import os
from dotenv import load_dotenv
from routes.productos import productos_bp
from routes.users import users_bp
from routes.sales import sales_bp
from routes.reports import reports_bp

#Cargar las Variables de entorno
load_dotenv()


#Iniciamos la APP
def create_app():
    #Instanciamos la app
    app= Flask(__name__)
    #configuracion del JWT secreto de .env
    app.config['JWT_SECRET_KEY']= os.getenv('JWT_SECRET_KEY')
    jwt=JWTManager(app)

    # Configurar tamaño máximo de archivo (5MB)
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

    #registramos el blueprint

    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(sales_bp, url_prefix='/api')
    app.register_blueprint(productos_bp, url_prefix='/productos')
    app.register_blueprint(reports_bp, url_prefix='/reportes')

    # Enedpoint para servir los archivo estaticos (imagenes)
    #return send_from_directory('static', filename)

    print(app.url_map)

    return app

app = create_app()

if __name__=='__main__':
    #obtenemos el puerto
    port= int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)

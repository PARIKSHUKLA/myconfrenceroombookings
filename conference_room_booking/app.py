from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def create_app():
    """Build and configure the Flask application.

    Sets up the SQLite database connection, registers the ``bookings``
    and ``rooms`` blueprints, defines the ``/health`` route, and ensures
    all tables exist (via ``db.create_all()``) before returning.

    Args:
        None.

    Returns:
        flask.Flask: A fully configured Flask application instance,
        ready to run (e.g. via ``app.run()``) or serve with a WSGI
        server.

    Examples:
        Example 1 - build the app and run the dev server::

            from app import create_app
            app = create_app()
            app.run(debug=True)

        Example 2 - build the app for use in a test client::

            from app import create_app
            app = create_app()
            client = app.test_client()
            response = client.get('/health')

        Browser / cURL:
            Not applicable — this is a Python factory function, not an
            HTTP route. Once the returned app is running, see the
            ``/health`` route below for a callable example.
    """
    app = Flask(__name__)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'db', 'bookings.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'workshop-secret-key'

    db.init_app(app)

    from routes.bookings import bookings_bp
    from routes.rooms import rooms_bp
    app.register_blueprint(bookings_bp)
    app.register_blueprint(rooms_bp)

    @app.route('/health')
    def health():
        """Report that the service is up.

        Route:
            GET /health

        Args:
            None.

        Returns:
            dict: ``{"status": "ok", "service": "conference-room-booking"}``,
            serialized by Flask to JSON with HTTP 200.

        Examples:
            Example 1 - basic health check::

                GET /health

            Example 2 - same call, explicit host/port::

                GET http://127.0.0.1:5000/health

            Browser:
                http://127.0.0.1:5000/health

            cURL:
                curl.exe http://127.0.0.1:5000/health
        """
        return {'status': 'ok', 'service': 'conference-room-booking'}

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)

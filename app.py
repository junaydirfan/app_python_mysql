import os
import time
from contextlib import contextmanager

import mysql.connector
from mysql.connector import IntegrityError
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is required")
    return value


app = Flask(__name__)
app.secret_key = require_env("FLASK_SECRET_KEY")

MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "mysql"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "appuser"),
    "password": require_env("MYSQL_PASSWORD"),
    "database": os.environ.get("MYSQL_DATABASE", "appdb"),
}


def get_db_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)


def wait_for_db(max_attempts=30, delay_seconds=2):
    last_error = None
    for _ in range(max_attempts):
        try:
            connection = get_db_connection()
            connection.close()
            return
        except mysql.connector.Error as exc:
            last_error = exc
            time.sleep(delay_seconds)

    raise RuntimeError("Unable to connect to MySQL after waiting") from last_error


@contextmanager
def db_cursor():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def init_db():
    wait_for_db()
    with db_cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            ) ENGINE=InnoDB
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                full_name VARCHAR(255),
                email VARCHAR(255),
                FOREIGN KEY (user_id) REFERENCES users(id)
            ) ENGINE=InnoDB
            """
        )


def password_is_valid(stored_password, submitted_password):
    try:
        return check_password_hash(stored_password, submitted_password)
    except ValueError:
        return stored_password == submitted_password


@app.route("/")
def health_check():
    return "App is running"


@app.route("/signup", methods=["GET", "POST"])
def signUp():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:
            return render_template("signup.html"), 400

        password_hash = generate_password_hash(password)
        try:
            with db_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (%s, %s)",
                    (username, password_hash),
                )
        except IntegrityError:
            return "Username already exists", 409

        return redirect(url_for("signin"))

    return render_template("signup.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        with db_cursor() as cursor:
            cursor.execute(
                "SELECT id, password FROM users WHERE username = %s",
                (username,),
            )
            user = cursor.fetchone()

            if user and password_is_valid(user[1], password):
                session["user_id"] = user[0]
                if user[1] == password:
                    cursor.execute(
                        "UPDATE users SET password = %s WHERE id = %s",
                        (generate_password_hash(password), user[0]),
                    )
                return redirect(url_for("dashboard"))

    return render_template("signin.html")


@app.route("/signout")
def signout():
    session.pop("user_id", None)
    return redirect(url_for("signin"))


@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("signin"))

    user_id = session["user_id"]
    with db_cursor() as cursor:
        cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            session.pop("user_id", None)
            return redirect(url_for("signin"))

        username = user[0]

        cursor.execute(
            "SELECT full_name, email FROM user_data WHERE user_id = %s",
            (user_id,),
        )
        profile = cursor.fetchone()
        full_name = profile[0] if profile else ""
        email = profile[1] if profile else ""

        cursor.execute(
            """
            SELECT users.username, user_data.full_name, user_data.email
            FROM user_data
            JOIN users ON user_data.user_id = users.id
            """
        )
        all_profiles = cursor.fetchall()

    return render_template(
        "dashboard.html",
        username=username,
        full_name=full_name,
        email=email,
        all_profiles=all_profiles,
    )


@app.route("/update", methods=["POST"])
def update_user_data():
    if "user_id" not in session:
        return redirect(url_for("signin"))

    user_id = session["user_id"]
    full_name = request.form.get("full_name")
    email = request.form.get("email")

    if full_name and email:
        with db_cursor() as cursor:
            cursor.execute("SELECT id FROM user_data WHERE user_id = %s", (user_id,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    "UPDATE user_data SET full_name = %s, email = %s WHERE user_id = %s",
                    (full_name, email, user_id),
                )
            else:
                cursor.execute(
                    "INSERT INTO user_data (user_id, full_name, email) VALUES (%s, %s, %s)",
                    (user_id, full_name, email),
                )

    return redirect(url_for("dashboard"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))

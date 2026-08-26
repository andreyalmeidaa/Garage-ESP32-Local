from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from functools import wraps
from typing import Optional

import requests
from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "banco.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = "Andrey#2026@1909"

ESP_REQUEST_TIMEOUT = 3

estado_portao = {
    "status": "Fechado",
    "ultimo_comando": "Sistema iniciado",
    "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception: Optional[BaseException]) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_display() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def init_db() -> None:
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_usuario TEXT NOT NULL UNIQUE,
            nome_completo TEXT NOT NULL,
            senha_hash TEXT NOT NULL,
            perfil TEXT NOT NULL CHECK(perfil IN ('admin', 'user')),
            ativo INTEGER NOT NULL DEFAULT 1,
            data_criacao TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS historico_comandos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario INTEGER NOT NULL,
            nome_usuario TEXT NOT NULL,
            acao TEXT NOT NULL,
            detalhes TEXT NOT NULL,
            data_criacao TEXT NOT NULL,
            FOREIGN KEY(id_usuario) REFERENCES usuarios(id)
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS configuracoes (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            ip_esp32 TEXT NOT NULL,
            alerta_seguranca TEXT NOT NULL,
            data_atualizacao TEXT NOT NULL,
            atualizado_por TEXT NOT NULL
        )
        """
    )
    db.commit()

    admin_exists = db.execute(
        "SELECT id FROM usuarios WHERE nome_usuario = ?",
        ("admin",)
    ).fetchone()

    if not admin_exists:
        db.execute(
            """
            INSERT INTO usuarios (
                nome_usuario,
                nome_completo,
                senha_hash,
                perfil,
                ativo,
                data_criacao
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "admin",
                "Administrador do Sistema",
                generate_password_hash("1234"),
                "admin",
                1,
                now_iso(),
            ),
        )

    settings_exists = db.execute(
        "SELECT id FROM configuracoes WHERE id = 1"
    ).fetchone()

    if not settings_exists:
        db.execute(
            """
            INSERT INTO configuracoes (
                id,
                ip_esp32,
                alerta_seguranca,
                data_atualizacao,
                atualizado_por
            )
            VALUES (1, ?, ?, ?, ?)
            """,
            (
                "192.168.0.6",
                "Verifique se não há pessoas ou veículos na área antes de acionar o portão.",
                now_iso(),
                "system",
            ),
        )

    db.commit()
    db.close()


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Apenas administradores podem acessar essa área.", "error")
            return redirect(url_for("dashboard"))
        return view_func(*args, **kwargs)

    return wrapped


def get_settings() -> sqlite3.Row:
    return get_db().execute(
        "SELECT * FROM configuracoes WHERE id = 1"
    ).fetchone()


def log_history(user_id: int, username: str, action: str, details: str) -> None:
    db = get_db()
    db.execute(
        """
        INSERT INTO historico_comandos (
            id_usuario,
            nome_usuario,
            acao,
            detalhes,
            data_criacao
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, username, action, details, now_iso()),
    )
    db.commit()


def update_gate_state(status: str, command: str) -> None:
    estado_portao["status"] = status
    estado_portao["ultimo_comando"] = command
    estado_portao["ultima_atualizacao"] = now_display()


def ensure_logged_user_is_valid() -> bool:
    if "user_id" not in session:
        return False

    user = get_db().execute(
        """
        SELECT id, nome_usuario, nome_completo, perfil, ativo
        FROM usuarios
        WHERE id = ?
        """,
        (session["user_id"],),
    ).fetchone()

    if not user or not user["ativo"]:
        session.clear()
        return False

    session["username"] = user["nome_usuario"]
    session["full_name"] = user["nome_completo"]
    session["role"] = user["perfil"]
    return True


@app.before_request
def protect_session():
    public_endpoints = {"login", "static"}
    if request.endpoint in public_endpoints:
        return
    if "user_id" in session:
        ensure_logged_user_is_valid()


@app.context_processor
def inject_user():
    return {
        "session_user": {
            "id": session.get("user_id"),
            "username": session.get("username"),
            "full_name": session.get("full_name"),
            "role": session.get("role"),
        }
    }


@app.route("/")
def home():
    if session.get("user_id") and ensure_logged_user_is_valid():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id") and ensure_logged_user_is_valid():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_db().execute(
            "SELECT * FROM usuarios WHERE nome_usuario = ?",
            (username,)
        ).fetchone()

        if not user or not check_password_hash(user["senha_hash"], password):
            flash("Usuário ou senha inválidos.", "error")
            return render_template("login.html")

        if not user["ativo"]:
            flash("Este usuário está desativado.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["nome_usuario"]
        session["full_name"] = user["nome_completo"]
        session["role"] = user["perfil"]

        flash("Login realizado com sucesso.", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Sessão encerrada com sucesso.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    if not ensure_logged_user_is_valid():
        return redirect(url_for("login"))

    db = get_db()
    history = db.execute(
        "SELECT * FROM historico_comandos ORDER BY id DESC LIMIT 8"
    ).fetchall()

    settings = get_settings()

    users_count = db.execute(
        "SELECT COUNT(*) AS total FROM usuarios WHERE ativo = 1"
    ).fetchone()["total"]

    return render_template(
        "dashboard.html",
        gate_state=estado_portao,
        history=history,
        settings=settings,
        users_count=users_count,
    )


@app.route("/minha-conta", methods=["GET", "POST"])
@login_required
def account_page():
    if not ensure_logged_user_is_valid():
        return redirect(url_for("login"))

    if request.method == "POST":
        action = request.form.get("action", "").strip()

        if action == "change_password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            user = get_db().execute(
                "SELECT * FROM usuarios WHERE id = ?",
                (session["user_id"],)
            ).fetchone()

            if not check_password_hash(user["senha_hash"], current_password):
                flash("A senha atual está incorreta.", "error")
                return redirect(url_for("account_page"))

            if len(new_password) < 4:
                flash("A nova senha deve ter pelo menos 4 caracteres.", "error")
                return redirect(url_for("account_page"))

            if new_password != confirm_password:
                flash("A confirmação da nova senha não confere.", "error")
                return redirect(url_for("account_page"))

            db = get_db()
            db.execute(
                "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                (generate_password_hash(new_password), session["user_id"]),
            )
            db.commit()

            log_history(
                session["user_id"],
                session["username"],
                "ALTERACAO_SENHA",
                "O usuário alterou a própria senha.",
            )
            flash("Senha alterada com sucesso.", "success")
            return redirect(url_for("account_page"))

        if action == "delete_account":
            current_password = request.form.get("delete_current_password", "")

            user = get_db().execute(
                "SELECT * FROM usuarios WHERE id = ?",
                (session["user_id"],)
            ).fetchone()

            if not user:
                session.clear()
                return redirect(url_for("login"))

            if user["nome_usuario"] == "admin":
                flash("O usuário admin padrão não pode excluir a própria conta.", "error")
                return redirect(url_for("account_page"))

            if not check_password_hash(user["senha_hash"], current_password):
                flash("Senha incorreta para excluir a conta.", "error")
                return redirect(url_for("account_page"))

            db = get_db()
            db.execute(
                "DELETE FROM historico_comandos WHERE id_usuario = ?",
                (session["user_id"],)
            )
            db.execute(
                "DELETE FROM usuarios WHERE id = ?",
                (session["user_id"],)
            )
            db.commit()

            session.clear()
            flash("Conta excluída com sucesso.", "success")
            return redirect(url_for("login"))

    return render_template("account.html")


@app.route("/usuarios")
@admin_required
def users_page():
    if not ensure_logged_user_is_valid():
        return redirect(url_for("login"))

    users = get_db().execute(
        """
        SELECT id, nome_usuario, nome_completo, perfil, ativo, data_criacao
        FROM usuarios
        ORDER BY id ASC
        """
    ).fetchall()

    return render_template("users.html", users=users)


@app.route("/usuarios/novo", methods=["POST"])
@admin_required
def create_user():
    full_name = request.form.get("full_name", "").strip()
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "user").strip()

    if not full_name or not username or not password:
        flash("Preencha nome, usuário e senha.", "error")
        return redirect(url_for("users_page"))

    if len(password) < 4:
        flash("A senha deve ter pelo menos 4 caracteres.", "error")
        return redirect(url_for("users_page"))

    if role not in {"admin", "user"}:
        flash("Perfil inválido.", "error")
        return redirect(url_for("users_page"))

    db = get_db()
    existing = db.execute(
        "SELECT id FROM usuarios WHERE nome_usuario = ?",
        (username,)
    ).fetchone()

    if existing:
        flash("Já existe um usuário com esse login.", "error")
        return redirect(url_for("users_page"))

    db.execute(
        """
        INSERT INTO usuarios (
            nome_usuario,
            nome_completo,
            senha_hash,
            perfil,
            ativo,
            data_criacao
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (username, full_name, generate_password_hash(password), role, 1, now_iso()),
    )
    db.commit()

    log_history(
        session["user_id"],
        session["username"],
        "CADASTRO_USUARIO",
        f"Usuário {username} criado com perfil {role}.",
    )
    flash("Usuário criado com sucesso.", "success")
    return redirect(url_for("users_page"))


@app.route("/usuarios/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id: int):
    db = get_db()
    user = db.execute(
        "SELECT * FROM usuarios WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not user:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("users_page"))

    if user["nome_usuario"] == "admin":
        flash("O usuário admin padrão não pode ser desativado.", "error")
        return redirect(url_for("users_page"))

    new_value = 0 if user["ativo"] else 1
    db.execute(
        "UPDATE usuarios SET ativo = ? WHERE id = ?",
        (new_value, user_id)
    )
    db.commit()

    acao = "ativado" if new_value else "desativado"
    log_history(
        session["user_id"],
        session["username"],
        "ALTERACAO_USUARIO",
        f"Usuário {user['nome_usuario']} foi {acao}.",
    )
    flash(f"Usuário {acao} com sucesso.", "success")
    return redirect(url_for("users_page"))


@app.route("/usuarios/<int:user_id>/excluir", methods=["POST"])
@admin_required
def delete_user(user_id: int):
    db = get_db()
    user = db.execute(
        "SELECT * FROM usuarios WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not user:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("users_page"))

    if user["nome_usuario"] == "admin":
        flash("O usuário admin padrão não pode ser excluído.", "error")
        return redirect(url_for("users_page"))

    if user["id"] == session.get("user_id"):
        flash("Use a opção da sua conta para excluir o próprio acesso.", "error")
        return redirect(url_for("users_page"))

    db.execute(
        "DELETE FROM historico_comandos WHERE id_usuario = ?",
        (user_id,)
    )
    db.execute(
        "DELETE FROM usuarios WHERE id = ?",
        (user_id,)
    )
    db.commit()

    log_history(
        session["user_id"],
        session["username"],
        "EXCLUSAO_USUARIO",
        f"Usuário {user['nome_usuario']} foi excluído.",
    )
    flash("Usuário excluído com sucesso.", "success")
    return redirect(url_for("users_page"))


@app.route("/configuracoes", methods=["GET", "POST"])
@admin_required
def settings_page():
    db = get_db()

    if request.method == "POST":
        esp32_ip = request.form.get("esp32_ip", "").strip()
        security_alert = request.form.get("security_alert", "").strip()

        if not esp32_ip:
            flash("Informe o IP do ESP32.", "error")
            return redirect(url_for("settings_page"))

        if not security_alert:
            flash("Informe o alerta de segurança.", "error")
            return redirect(url_for("settings_page"))

        db.execute(
            """
            UPDATE configuracoes
            SET ip_esp32 = ?, alerta_seguranca = ?, data_atualizacao = ?, atualizado_por = ?
            WHERE id = 1
            """,
            (esp32_ip, security_alert, now_iso(), session["username"]),
        )
        db.commit()

        log_history(
            session["user_id"],
            session["username"],
            "CONFIGURACAO",
            f"IP do ESP32 alterado para {esp32_ip}.",
        )
        flash("Configurações atualizadas com sucesso.", "success")
        return redirect(url_for("settings_page"))

    settings = get_settings()
    return render_template("settings.html", settings=settings)


@app.route("/historico")
@login_required
def history_page():
    if not ensure_logged_user_is_valid():
        return redirect(url_for("login"))

    history = get_db().execute(
        "SELECT * FROM historico_comandos ORDER BY id DESC LIMIT 100"
    ).fetchall()

    return render_template("history.html", history=history)


@app.route("/api/status")
@login_required
def api_status():
    if not ensure_logged_user_is_valid():
        return jsonify({"ok": False, "mensagem": "Sessão inválida."}), 401

    settings = get_settings()
    history = get_db().execute(
        "SELECT * FROM historico_comandos ORDER BY id DESC LIMIT 8"
    ).fetchall()

    history_json = [
        {
            "id": item["id"],
            "username": item["nome_usuario"],
            "action": item["acao"],
            "details": item["detalhes"],
            "created_at": item["data_criacao"],
        }
        for item in history
    ]

    return jsonify({
        "ok": True,
        "status": estado_portao["status"],
        "ultimo_comando": estado_portao["ultimo_comando"],
        "ultima_atualizacao": estado_portao["ultima_atualizacao"],
        "esp32_ip": settings["ip_esp32"],
        "security_alert": settings["alerta_seguranca"],
        "history": history_json,
    })


@app.route("/api/comando/<acao>", methods=["POST"])
@login_required
def api_command(acao: str):
    if not ensure_logged_user_is_valid():
        return jsonify({"ok": False, "mensagem": "Sessão inválida."}), 401

    map_status = {
        "abrir": ("Aberto", "Comando de abrir enviado"),
        "fechar": ("Fechado", "Comando de fechar enviado"),
        "parar": ("Parado", "Comando de parada enviado"),
    }

    if acao not in map_status:
        return jsonify({"ok": False, "mensagem": "Comando inválido."}), 400

    settings = get_settings()
    esp32_ip = settings["ip_esp32"].strip()

    if not esp32_ip:
        return jsonify({"ok": False, "mensagem": "IP do ESP32 não configurado."}), 400

    url = f"http://{esp32_ip}/{acao}"

    try:
        resposta = requests.get(
            url,
            timeout=ESP_REQUEST_TIMEOUT,
            proxies={"http": None, "https": None},
        )

        if resposta.status_code != 200:
            return jsonify({
                "ok": False,
                "mensagem": f"ESP32 respondeu com erro HTTP {resposta.status_code}."
            }), 502

        status, comando = map_status[acao]
        update_gate_state(status, comando)

        log_history(
            session["user_id"],
            session["username"],
            acao.upper(),
            f"{session['username']} acionou {acao} no portão. IP do ESP32: {esp32_ip}",
        )

        return jsonify({
            "ok": True,
            "mensagem": f"Comando '{acao}' enviado ao ESP32 com sucesso.",
            "resposta_esp32": resposta.text,
            "estado": {
                "status": estado_portao["status"],
                "ultimo_comando": estado_portao["ultimo_comando"],
                "ultima_atualizacao": estado_portao["ultima_atualizacao"],
            },
        })

    except requests.exceptions.ConnectTimeout:
        return jsonify({
            "ok": False,
            "mensagem": "Tempo esgotado ao conectar no ESP32."
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            "ok": False,
            "mensagem": f"Não foi possível conectar ao ESP32 em {esp32_ip}."
        }), 502

    except requests.exceptions.RequestException as exc:
        return jsonify({
            "ok": False,
            "mensagem": f"Erro ao comunicar com o ESP32: {str(exc)}"
        }), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
else:
    init_db()
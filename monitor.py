import time
import pytz
import os
import logging
from dotenv import load_dotenv
import pymysql
from datetime import datetime, timedelta
import html
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class GLPIMonitor:
    """Monitora o banco de dados do GLPI em busca de novos tickets e acompanhamentos."""

    @staticmethod
    def normalize_html_text(text):
        if not text:
            return ""
        text = html.unescape(text)
        soup = BeautifulSoup(text, "html.parser")
        texto_formatado = soup.get_text(separator="\n")
        return texto_formatado.strip()

    def __init__(self, config):
        self.db_config = {
            "host": config["DB_HOST"],
            "user": config["DB_USER"],
            "password": config["DB_PASSWORD"],
            "database": config["DB_NAME"],
            "cursorclass": pymysql.cursors.DictCursor,
        }
        self.status_map = {
            1: "Novo",
            2: "Processando (atribuído)",
            3: "Processando (planejado)",
            4: "Pendente",
            5: "Solucionado",
            6: "Fechado",
        }

    def _get_db_connection(self):
        """Estabelece uma conexão com o banco de dados."""
        try:
            return pymysql.connect(**self.db_config)
        except pymysql.MySQLError as e:
            logging.error(f"Erro ao conectar ao banco de dados GLPI: {e}")
            return None

    def get_new_tickets(self, interval_minutes=3):
        """Busca por novos tickets criados no intervalo de tempo."""
        conn = self._get_db_connection()
        if not conn:
            return []
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                tz = pytz.timezone("America/Sao_Paulo")
                time_threshold = datetime.now(tz) - timedelta(minutes=interval_minutes)
                logging.info(
                    f"Buscando tickets criados desde {time_threshold.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                sql = """
                    SELECT
                        t.id,
                        t.name,
                        t.content,
                        t.date_creation,
                        t.date_mod,
                        t.status,
                        req_user.name AS requester_name,
                        req_email.email AS requester_email,
                        tech_user.name AS technician_name,
                        req_user.phone AS phone,
                        tech_email.email AS technician_email
                    FROM glpi_tickets AS t
                    -- Join para encontrar o Solicitante do ticket (type=1)
                    LEFT JOIN glpi_tickets_users AS req_tu
                    ON t.id = req_tu.tickets_id
                    AND req_tu.type = 1
                    LEFT JOIN glpi_users AS req_user
                    ON req_tu.users_id = req_user.id
                    LEFT JOIN glpi_useremails AS req_email
                    ON req_user.id = req_email.users_id
                    AND req_email.is_default = 1
                    -- Join para encontrar o Técnico Atribuído ao ticket (type=2)
                    LEFT JOIN glpi_tickets_users AS tech_tu
                    ON t.id = tech_tu.tickets_id AND tech_tu.type = 2
                    LEFT JOIN glpi_users AS tech_user
                    ON tech_tu.users_id = tech_user.id
                    LEFT JOIN glpi_useremails AS tech_email
                    ON tech_user.id = tech_email.users_id
                    AND tech_email.is_default = 1
                    WHERE t.date_creation >= %s
                    ORDER BY t.date_creation DESC;
                    """
                cursor.execute(sql, (time_threshold,))
                chamados = cursor.fetchall()
                # Remove tags HTML do campo content
                for chamado in chamados:
                    chamado["content"] = self.normalize_html_text(chamado["content"])
                return chamados
        except pymysql.MySQLError as e:
            logging.error(f"Erro ao buscar acompanhamentos: {e}")
            return []
        finally:
            conn.close()

    def get_close_tickets(self, interval_minutes=3):
        """Busca por tickets fechados no intervalo de tempo."""
        conn = self._get_db_connection()
        if not conn:
            return []
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                tz = pytz.timezone("America/Sao_Paulo")
                time_threshold = datetime.now(tz) - timedelta(minutes=interval_minutes)
                logging.info(
                    f"Buscando tickets fechados desde {time_threshold.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                sql = """
                    SELECT
                        t.id,
                        t.name,
                        s.content,
                        t.date_creation,
                        t.date_mod,
                        t.status,
                        req_user.name AS requester_name,
                        req_email.email AS requester_email,
                        req_user.phone AS phone,
                        tech_user.name AS technician_name,
                        tech_email.email AS technician_email
                    FROM glpi_tickets AS t
                    -- Join para pegar a descrição da solução
                    LEFT JOIN glpi_itilsolutions AS s
                    ON t.id = s.items_id
                    -- Join para encontrar o Solicitante do ticket (type=1)
                    LEFT JOIN glpi_tickets_users AS req_tu
                    ON t.id = req_tu.tickets_id
                    AND req_tu.type = 1
                    LEFT JOIN glpi_users AS req_user
                    ON req_tu.users_id = req_user.id
                    LEFT JOIN glpi_useremails AS req_email
                    ON req_user.id = req_email.users_id
                    AND req_email.is_default = 1
                    -- Join para encontrar o Técnico Atribuído ao ticket (type=2)
                    LEFT JOIN glpi_tickets_users AS tech_tu
                    ON t.id = tech_tu.tickets_id AND tech_tu.type = 2
                    LEFT JOIN glpi_users AS tech_user
                    ON tech_tu.users_id = tech_user.id
                    LEFT JOIN glpi_useremails AS tech_email
                    ON tech_user.id = tech_email.users_id
                    AND tech_email.is_default = 1
                    WHERE t.date_mod >= %s
                    AND t.status = 6
                    ORDER BY t.date_mod DESC;
                    """
                cursor.execute(sql, (time_threshold,))
                chamados = cursor.fetchall()
                # Remove tags HTML do campo content
                for chamado in chamados:
                    chamado["content"] = self.normalize_html_text(chamado["content"])
                return chamados
        except pymysql.MySQLError as e:
            logging.error(f"Erro ao buscar acompanhamentos: {e}")
            return []
        finally:
            conn.close()

    def get_new_validations(self, interval_minutes=3):
        """Busca por novos tickets criados no intervalo de tempo."""
        conn = self._get_db_connection()
        if not conn:
            return []
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                tz = pytz.timezone("America/Sao_Paulo")
                time_threshold = datetime.now(tz) - timedelta(minutes=interval_minutes)
                logging.info(
                    f"Buscando aprovações de tickets desde {time_threshold.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                sql = """
                    SELECT
                        t.id,
                        t.name,
                        t.content,
                        v.comment_submission,
                        t.date_creation,
                        t.date_mod,
                        t.status,
                        req_user.name AS requester_name,
                        req_user.phone AS phone,
                        val_user.name AS validator_name,
                        val_user.phone AS validator_phone
                    FROM glpi_tickets AS t
                    -- Join para pegar a validação
                    LEFT JOIN glpi_ticketvalidations AS v
                    ON t.id = v.tickets_id
                    -- Join para encontrar o Solicitante do ticket (type=1)
                    LEFT JOIN glpi_tickets_users AS req_tu
                    ON t.id = req_tu.tickets_id
                    AND req_tu.type = 1
                    -- Join para encontrar o usuario Atribuído ao ticket
                    LEFT JOIN glpi_users AS req_user
                    ON req_tu.users_id = req_user.id
                    -- Join para encontrar o Técnico Atribuído ao a validação
                    LEFT JOIN glpi_users AS val_user
                    ON v.users_id = val_user.id
                    WHERE t.date_mod >= %s
                    and v.status = 2
                    ORDER BY t.date_mod DESC;
                    """
                cursor.execute(sql, (time_threshold,))
                chamados = cursor.fetchall()
                # Remove tags HTML do campo content
                for chamado in chamados:
                    chamado["content"] = self.normalize_html_text(chamado["content"])
                    chamado["comment_submission"] = self.normalize_html_text(
                        chamado["comment_submission"]
                    )
                return chamados
        except pymysql.MySQLError as e:
            logging.error(f"Erro ao buscar acompanhamentos: {e}")
            return []
        finally:
            conn.close()

    def get_new_followups(self, interval_minutes=3):
        """Busca por novos acompanhamentos criados no intervalo de tempo."""
        conn = self._get_db_connection()
        if not conn:
            return []

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                tz = pytz.timezone("America/Sao_Paulo")
                time_threshold = datetime.now(tz) - timedelta(minutes=interval_minutes)
                logging.info(
                    f"Buscando acompanhamentos criados desde {time_threshold.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                sql = """
                    SELECT
                        f.id,
                        f.items_id AS ticket_id,
                        f.content,
                        f.date_creation,
                        t.name AS ticket_title,
                        author.name AS author_name,
                        author_email.email AS author_email,
                        req_user.name AS requester_name,
                        req_user.phone AS phone,
                        req_email.email AS requester_email,
                        tech_user.name AS technician_name,
                        tech_email.email AS technician_email
                    FROM glpi_itilfollowups AS f
                    -- Join para pegar o título do ticket
                    INNER JOIN glpi_tickets AS t ON f.items_id = t.id
                    -- Join para pegar o autor do acompanhamento
                    LEFT JOIN glpi_users AS author ON f.users_id = author.id
                    LEFT JOIN glpi_useremails AS author_email
                    ON author.id = author_email.users_id
                    AND author_email.is_default = 1
                    -- Join para encontrar o Solicitante do ticket (type=1)
                    LEFT JOIN glpi_tickets_users AS req_tu
                    ON t.id = req_tu.tickets_id
                    AND req_tu.type = 1
                    LEFT JOIN glpi_users AS req_user
                    ON req_tu.users_id = req_user.id
                    LEFT JOIN glpi_useremails AS req_email
                    ON req_user.id = req_email.users_id
                    AND req_email.is_default = 1
                    -- Join para encontrar o Técnico Atribuído ao ticket (type=2)
                    LEFT JOIN glpi_tickets_users AS tech_tu
                    ON t.id = tech_tu.tickets_id AND tech_tu.type = 2
                    LEFT JOIN glpi_users AS tech_user
                    ON tech_tu.users_id = tech_user.id
                    LEFT JOIN glpi_useremails AS tech_email
                    ON tech_user.id = tech_email.users_id
                    AND tech_email.is_default = 1
                    WHERE f.itemtype = 'Ticket'
                    AND f.is_private = 0
                    AND f.date_creation >= %s
                    ORDER BY f.date_creation DESC;
                    """
                cursor.execute(sql, (time_threshold,))
                followups = cursor.fetchall()
                # Remove tags HTML do campo content
                for followup in followups:
                    followup["content"] = self.normalize_html_text(followup["content"])
                logging.info(
                    f"Query de acompanhamentos retornou {len(followups)} resultados"
                )
                for i, followup in enumerate(followups):
                    logging.info(
                        f"Acompanhamento {i+1}: ID={followup['id']}, ticket_id={followup['ticket_id']}, author_email={followup['author_email']}, requester_email={followup['requester_email']}, technician_email={followup['technician_email']}"
                    )
                return followups
        except pymysql.MySQLError as e:
            logging.error(f"Erro ao buscar acompanhamentos: {e}")
            return []
        finally:
            conn.close()


def __main__():
    """Função principal para executar o monitoramento."""
    load_dotenv()
    config = {
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_NAME": os.getenv("DB_NAME"),
    }
    monitor = GLPIMonitor(config)
    while True:
        logging.info(f"Conectando ao banco de dados GLPI: {config['DB_HOST']}")
        followups = monitor.get_new_followups()
        if followups:
            logging.info(f"Encontrados {len(followups)} novos acompanhamentos.")
            for followup in followups:
                logging.info(
                    f"Acompanhamento ID: {followup['id']}, Ticket: {followup['ticket_title']}, Autor: {followup['author_name']}, Data: {followup['date_creation']}"
                )
                if followup["phone"]:
                    from services.chamada_notificacao import enviar_notificacao

                    mensagem = (
                        f"💬 Novo acompanhamento\n"
                        f"{followup['author_name']} adicionou um acompanhamento no chamado #{followup['ticket_id']}.\n"
                        f"Título do chamado: {followup['ticket_title']}\n"
                        f"Mensagem Adicionada: {followup['content']}\n"
                        f"Registrado em: {followup['date_creation']}\n"
                        f"Clique para ver o chamado⬇️: \nhttp://{os.getenv('GLPI_URL')}/front/ticket.form.php?id={followup['ticket_id']}\n"
                    )
                    enviar_notificacao(mensagem, followup["phone"])
        else:
            logging.info("Nenhum novo acompanhamento encontrado.")
        tickets = monitor.get_new_tickets()
        if tickets:
            logging.info(f"Encontrados {len(tickets)} novos tickets.")
            for ticket in tickets:
                logging.info(
                    f"Ticket ID: {ticket['id']}, Título: {ticket['name']}, Solicitante: {ticket['requester_name']}, Data: {ticket['date_creation']}"
                )
                if ticket["phone"]:
                    from services.chamada_notificacao import enviar_notificacao

                    mensagem = (
                        f"🎫 Novo chamado GLPI\n"
                        f"ID: {ticket['id']}\n"
                        f"Título: {ticket['name']}\n"
                        f"Solicitante: {ticket['requester_name']}\n"
                        f"Descrição: {ticket['content']}\n"
                        f"Registrado em: {ticket['date_creation']}\n"
                        f"Clique para ver o chamado⬇️: \nhttp://{os.getenv('GLPI_URL')}/front/ticket.form.php?id={ticket['id']}\n"
                    )
                    enviar_notificacao(mensagem, ticket["phone"])
        else:
            logging.info("Nenhum novo ticket encontrado.")
        closed_tickets = monitor.get_close_tickets()
        if closed_tickets:
            logging.info(f"Encontrados {len(closed_tickets)} tickets fechados.")
            for ticket in closed_tickets:
                logging.info(
                    f"Ticket ID: {ticket['id']}, Título: {ticket['name']}, Solicitante: {ticket['requester_name']}, Data de fechamento: {ticket['date_mod']}"
                )
                if ticket["phone"]:
                    from services.chamada_notificacao import enviar_notificacao

                    mensagem = (
                        f"✅ Chamado Fechado!\n"
                        f"ID: {ticket['id']}\n"
                        f"Título: {ticket['name']}\n"
                        f"Solicitante: {ticket['requester_name']}\n"
                        f"Data de fechamento: {ticket['date_mod']}\n"
                        f"Solução: {ticket['content']}\n"
                        f"Clique para ver o chamado⬇️: \nhttp://{os.getenv('GLPI_URL')}/front/ticket.form.php?id={ticket['id']}\n"
                    )
                    enviar_notificacao(mensagem, ticket["phone"])
        else:
            logging.info("Nenhum ticket fechado encontrado.")
        validations = monitor.get_new_validations()
        if validations:
            logging.info(f"Encontradas {len(validations)} novas aprovações.")
            for validation in validations:
                logging.info(
                    f"Ticket ID: {validation['id']}, Título: {validation['name']}, Solicitante: {validation['requester_name']}, Validador: {validation['validator_name']}, Data: {validation['date_mod']}"
                )
                if validation["phone"]:
                    from services.chamada_notificacao import enviar_notificacao

                    mensagem = (
                        f"☑️ Foi solicitada a aprovação do seu chamado!\n"
                        f"ID: {validation['id']}\n"
                        f"Título: {validation['name']}\n"
                        f"Solicitante: {validation['requester_name']}\n"
                        f"Validador: {validation['validator_name']}\n"
                        f"Comentário da Solicitação: {validation['comment_submission']}\n"
                        f"Registrado em: {validation['date_mod']}\n"
                        f"Clique para ver o chamado⬇️: \nhttp://{os.getenv('GLPI_URL')}/front/ticket.form.php?id={validation['id']}\n"
                    )
                    enviar_notificacao(mensagem, validation["phone"])
        else:
            logging.info("Nenhuma nova aprovação encontrada.")
        time.sleep(180)


if __name__ == "__main__":
    logging.info("Monitor de banco iniciado")
    __main__()

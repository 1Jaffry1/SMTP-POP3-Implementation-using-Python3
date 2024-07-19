import threading

import smtp_server, pop3_server, DbCommands

if __name__ == "__main__":
    DbCommands.setup_database()
    pop3_server = pop3_server.POP3Server("POP3", "0.0.0.0", 110)
    smtp_server = smtp_server.SMTPServer("SMTP", "0.0.0.0", 25)
    threading.Thread(target=pop3_server.start_server).start()
    threading.Thread(target=smtp_server.start_server).start()

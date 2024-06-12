def HELO(domain):
    return f'HELO, {domain} at your service!\r\n'


def MAIL_FROM(email):
    return f"250 SENDER OK\r\n"



def RCPT_TO(email):
    return f"250 RECIPIENT OK\r\n"


def email_splitter(email : str):
    email = email.removeprefix("<").removesuffix(">")
    return email


def DATA():
    return "354 End data with single . on line\r\n"


def end_of_data(data_lines):
    return "250 OK: Message accepted for delivery\r\n"


def QUIT():
    return "221 Bye\r\n"
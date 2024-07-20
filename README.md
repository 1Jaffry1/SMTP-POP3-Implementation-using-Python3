# SMTP and POP3 Email Server

This is an implementation of an email server that uses an SMTP server that listens on port 25 and supports mail sending.
Mail receiving is achieved using a POP3 server that listens on port 110 and supports mail retrieval. The servers interact
using a common database, meaning you will need to create a user account in any one of the two servers. You can achieve that using
the `HELO` and `EHLO` commands in the SMTP server, or the `USER` command in the POP3 server.

- Multithreading is supported
- Authentication supported
- Email data is not secured, it is stored in plain text in the database
- sqlite3 is used for DB
## How to use
1. Clone the repository
2. Run the `main.py` file
3. Use a client like `telnet` or `nc` on MacOS to connect to the servers (in terminal, enter `telnet localhost 25` for SMTP or `telnet localhost 110` for POP3)
4. Use the commands listed below to interact with the servers
5. Use QUIT to close a connection
##


### Commands for SMTP server:

1- `HELO <username>` - to create a new user account (No authentication will be done, not secure, it cannot log-into secure accounts)

2- `EHLO <username>` - to create a new user account (Authentication will be done, secure, saves the password as a hash to the DB)

3- `MAIL FROM: <sender>` - to specify the sender of the email, sender must be `@ME` or the username.

4- `RCPT TO: <receiver>` - to specify the receiver of the email, receiver must be an existing user, multiple recievers are supported.

5- `DATA` - announces that you are ready to enter the body of the message (aka enter data mode). Data mode can be exited by sending a single `.` on a new line.

6- `QUIT` - to close the connection.

#
### Commands for the POP3 server:

1- `USER <username>` - to log into an existing user account, or create a new user account.

2- `PASS <password>` - to authenticate the user.

3- `STAT` - displays a summary of the mailbox. Format: `number of emails, total size of mailbox in bytes`

4- `LIST` - to list all the emails in the user's mailbox. Output format is: `email_id, sender, subject, email_size`

5- `RETR <email_id>` - to retrieve an email from the mailbox. Output format is: `email_id, sender, subject, email_body`

   `RETR` - to retrieve all emails from the mailbox.

   `RETR` U - to retrieve unread emails from the mailbox. (Not implemented yet)

6- `DELE <email_id>` - to delete an email from the mailbox.

7- `QUIT` - to close the connection.

<hr>

## Implementation Details

### Server Parent Class:
This class is the parent class for both the SMTP and POP3 servers. It contains the following methods:

`__init__()`: Initializes the server with the given port number and the server type, and sets logger specific to each server

`start_server()`: Starts the server and listens for incoming connections, listens upto 5 connections at a time using threading.

`handle_client()`: Abstracted method, handles the client connection, reads the incoming data and sends the response back to the client. This method is implemented in the child classes.

### SMTP Server

This class is a child class of the Server class. It contains the following functionalities:

1. Implements the `handle_client()` method to handle the SMTP client connection. It reads the incoming data from the client and sends the response back to the client. It is setup as a FSM to handle the SMTP commands, and their order.

    1. It initializes variables, such as the current state, the sender of the email, the data and the recipient list.
   2. It splits the command sent by the user, and passes the arguments to the respective function based on the command type.
   3. Manages user authentication status using the `login` variable. 

2. `HELO`: Checks if a user with the provided username exists already. If so, if the username has a password set, it will not allow login.
3. `EHLO`: Checks if a user with the provided username exists already. If the user exists and has a password set, it will prompt the user to enter the password, if the password field is empty, it will prompt the user to set a password. If user does not exist, it will create a new user, and set a password.
4. `MAIL FROM`: Sets the sender of the email. The sender must be `@ME` or the username.
5. `RCPT TO`: Sets the receivers of the email. The receivers are added to a list, and multiple receivers are supported. The function connects to the database and checks each of the users at the time they are added.
6. `DATA`: Enters the data mode, and reads the email body. The email body is stored as a string, and is sent to the socket line by line until `.` is sent on a new line. The message will be stored in the database.
7. 
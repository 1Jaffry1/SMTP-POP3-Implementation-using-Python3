# SMTP and POP3 Email Server

This is an implementation of an email server that uses an SMTP server that listens on port 25 and supports mail sending.
Mail receiving is achieved using a POP3 server that listens on port 110 and supports mail retrieval. The servers interact
using a common database, meaning you will need to create a user account in any one of the two servers. You can achieve that using
the `HELO` and `EHLO` commands in the SMTP server, or the `USER` command in the POP3 server.

- Multithreading is supported
- Authentication supported
- Email data is not secured, it is stored in plain text in the database
#
Commands for SMTP server:

1- `HELO <username>` - to create a new user account (No authentication will be done, not secure, it cannot log-into secure accounts)

2- `EHLO <username>` - to create a new user account (Authentication will be done, secure, saves the password as a hash to the DB)

3- `MAIL FROM: <sender>` - to specify the sender of the email, sender must be `@ME` or the username.

4- `RCPT TO: <receiver>` - to specify the receiver of the email, receiver must be an existing user, multiple recievers are supported.

5- `DATA` - announces that you are ready to enter the body of the message (aka enter data mode). Data mode can be exited by sending a single `.` on a new line.

6- `QUIT` - to close the connection.

#
Commands for the POP3 server:

1- `USER <username>` - to log into an existing user account, or create a new user account.

2- `PASS <password>` - to authenticate the user.

3- `STAT` - displays a summary of the mailbox. Format: `number of emails, total size of mailbox in bytes`

4- `LIST` - to list all the emails in the user's mailbox. Output format is: `email_id, sender, subject, email_size`

5- `RETR <email_id>` - to retrieve an email from the mailbox. Output format is: `email_id, sender, subject, email_body`

   `RETR` - to retrieve all emails from the mailbox.

   `RETR` U - to retrieve unread emails from the mailbox. (Not implemented yet)

6- `DELE <email_id>` - to delete an email from the mailbox.

7- `QUIT` - to close the connection.



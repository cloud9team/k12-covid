from werkzeug.security import check_password_hash, generate_password_hash
from handlers import db_covid
from handlers.db_covid import check_user_exists, add_user


value = input("Enter username:\n")

username = str(value)

if username != '':
    print(f'Username: {username}')
    value2 = input("Enter Password:\n")
    password = str(value2)
if (username != '' and password != ''):
    print(f'Adding {username}, {password} to database')
    msg = ''
    with db_covid.session_scope() as session:
        userData = check_user_exists(session, username, check_password_hash(password, password))
        if userData is None:
            add_user(session, username, generate_password_hash(password))
            msg = 'User added to database.'
        else:
            msg = 'User already in Database. Try a different username.'
print(msg)

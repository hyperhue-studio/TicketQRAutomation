import mysql.connector
import random
import string
import sys
import urllib.request
from PIL import Image
import qrcode
import smtplib
from email.message import EmailMessage

# --------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------

def get_random_string(length=12):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))

def connect(host='http://google.com'):
    try:
        urllib.request.urlopen(host)
        return True
    except:
        return False

def generate_qr(data, bg_image_path, pos, qr_size, save_path):
    qr = qrcode.QRCode(
        version=1,
        box_size=14,
        border=4
    )
    
    qr.add_data(data)
    qr.make(fit=True)
    
    img_qr = qr.make_image(fill_color='black', back_color='white')
    img_qr = img_qr.resize(qr_size)

    img_bg = Image.open(bg_image_path)

    img_bg.paste(img_qr, pos)

    img_bg.save(save_path)
    print(f"QR GENERATED AND SAVED IN {save_path}")
    
    qr.clear()

def send_mail(user_mail, user_password, receiver, subject, body, attachment_path):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = user_mail
    msg['To'] = receiver
    msg.set_content(body)

    with open(attachment_path, 'rb') as f:
        file_data = f.read()
        file_name = f.name
    msg.add_attachment(file_data, maintype='image', subtype='png', filename=file_name)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(user_mail, user_password)
            smtp.send_message(msg)
        print(f"Mail sent to {receiver}")
    except Exception as e:
        print(f"Error sending mail to {receiver}: {e}")

# --------------------------------------------------------------------
# Program start
# --------------------------------------------------------------------

if not connect():
    print('Internet connection failed. Please check your connection and try again.')
    sys.exit()

print('Internet connection successful.')

try:
    php_db = mysql.connector.connect(
        host="50.63.2.227",
        username="dummy_user",
        password="dummy_password",
        database="dummy_db"
    )
    print('Successfully connected to remote database!')
except:
    print('Error connecting to remote database')
    sys.exit()

try:
    db_local = mysql.connector.connect(
        host="localhost",
        username="root",
        password="dummy_password",
        database="dummy_db"
    )
    print('Successfully connected to local database!')
except:
    print('Error connecting to local database')
    sys.exit()

php_sales_cursor = php_db.cursor()
php_sales_cursor.execute("SELECT order_item_id, product_qty, order_item_name, email FROM tickets_sales")
php_sales_join = php_sales_cursor.fetchall()

db_local_cursor = db_local.cursor()
db_local_cursor.execute("SELECT order_item_id, product_qty, order_item_name, email FROM tickets_sales")
php_sales_table = db_local_cursor.fetchall()

php_set_join = set(php_sales_join)
php_set_sale = set(php_sales_table)

php_sales_differences = php_set_sale.symmetric_difference(php_set_join)

if not php_sales_differences:
    print('No differences were found. Exiting program.')
    sys.exit()

print('Found differences:', php_sales_differences)

php_list_differences = [list(item) for item in php_sales_differences]

# --------------------------------------------------------------------
# QR CODE GENERATION, EMAIL SENDING AND DATABASE UPDATE
# --------------------------------------------------------------------

user_mail = input("Enter your email: ")
user_password = input("Enter your password: ")

for element in sorted(php_list_differences, key=lambda x: x[0]):
    order_item_id = element[0]
    product_qty = element[1]
    order_item_name = element[2]
    email = element[3]
    code = get_random_string()

    insertion = f"INSERT INTO tickets_sales VALUES (0, {order_item_id}, {product_qty}, '{order_item_name}', '{email}', '{code}', 'SENT', 'NOT_GIVEN')"
    db_local_cursor.execute(insertion)
    db_local.commit()

    qr_data = f"{code},{email},{product_qty}"
    
    if order_item_name == "General Ticket":
        bg_image = 'backgrounds/general.png'
        save_path = f'QRSales/GENERAL_TICKET_QR_{order_item_id}.png'
        pos = (204, 624)
        qr_size = (670, 670)
    elif order_item_name == "VIP Ticket":
        bg_image = 'backgrounds/vip.png'
        save_path = f'QRSales/VIP_TICKET_QR_{order_item_id}.png'
        pos = (204, 624)
        qr_size = (670, 670)
    else:
        print(f'element {order_item_name} is not a valid ticket name. Skipping...')
        continue

    generate_qr(qr_data, bg_image, pos, qr_size, save_path)

    subject = f'Ticket {order_item_name} - {order_item_id}'
    body = f"Dear {email},\n\nPlease find attached your {order_item_name} ticket with the QR code for entry. Quantity: {product_qty}.\n\nThank you for your purchase."
    send_mail(user_mail, user_password, email, subject, body, save_path)

print('QR generation and email sending process completed.')
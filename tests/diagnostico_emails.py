from src.exchange_connector import get_account
import logging

logging.basicConfig(level=logging.INFO)

def diag():
    try:
        account = get_account()
        print(f"Bandeja: {account.inbox}")
        print(f"Total count (attr): {account.inbox.total_count}")
        
        all_emails = account.inbox.all()
        real_count = all_emails.count()
        print(f"Conteo real con .count(): {real_count}")
        
        latest = all_emails.order_by('-datetime_received')[:5]
        print("Últimos 5 correos encontrados:")
        for i, item in enumerate(latest):
            print(f"{i+1}. [{item.datetime_received}] {item.subject} (de {item.sender.email_address if item.sender else '?'})")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    diag()

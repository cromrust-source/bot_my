from config import CARD_NUMBER

def create_payment_link(amount: float) -> str:
    return f"https://www.tbank.ru/card/{CARD_NUMBER}?amount={amount}"
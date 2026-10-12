from ui.pages.main_page import setup_main_page
from ui.pages.adv_page import setup_adv_page

def setup_routes():
    """Регистрация всех страниц и маршрутов UI"""
    setup_main_page()
    setup_adv_page()
from kivy.config import Config
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'resizable', False)

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from database import init_db
from screens.login import LoginScreen
from screens.admin import AdminScreen
from screens.kasir import KasirScreen
from screens.laporan import LaporanScreen

init_db()

class KasirPOS(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(AdminScreen(name="admin"))
        sm.add_widget(KasirScreen(name="kasir"))
        sm.add_widget(LaporanScreen(name="laporan"))
        return sm

if __name__ == "__main__":
    KasirPOS().run()

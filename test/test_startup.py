from app.main import create_app
def test_app_starts(): assert create_app().title == "Asistente Comercial ACLIMAR"

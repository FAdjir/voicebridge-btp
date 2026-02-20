from app.main import format_for_human

def test_format_standard():
    # Donnée d'entrée simulée (ce que Gemini renvoie)
    fake_data = {
        "intervention": {
            "client": "M. Test",
            "status": "Terminé",
            "billing_items": [
                {"item": "Vis", "type": "Matériel", "note": "Boite de 100"}
            ]
        },
        "reminder": {"task": "Rien", "due_date": "Jamais"}
    }

    # Exécution
    result = format_for_human(fake_data)

    # Vérifications (Assertions)
    assert "M. Test" in result
    assert "Vis" in result
    assert "Boite de 100" in result
    assert "✅" in result
import subprocess
import sys
import os
import time
from datetime import datetime

def run_script_in_new_terminal(script_path, script_name):
    """
    Lance un script Python dans un nouveau terminal
    """
    try:
        if os.name == 'nt':  # Windows
            # Pour Windows, utiliser start pour ouvrir une nouvelle fenêtre cmd
            cmd = f'start cmd /k "python {script_path} && pause"'
            process = subprocess.Popen(cmd, shell=True)
            print(f"✅ Terminal ouvert pour {script_name}")    
        elif sys.platform == 'darwin':  # macOS
            # Pour macOS, utiliser osascript pour ouvrir un nouveau terminal
            cmd = f'''osascript -e 'tell app "Terminal" to do script "cd {os.getcwd()} && python3 {script_path}"'''
            process = subprocess.Popen(cmd, shell=True)
            print(f"✅ Terminal ouvert pour {script_name}")
            
        else:  # Linux
            # Pour Linux, utiliser gnome-terminal ou xterm
            try:
                cmd = f'gnome-terminal -- python3 {script_path}'
                process = subprocess.Popen(cmd, shell=True)
            except:
                cmd = f'xterm -e python3 {script_path}'
                process = subprocess.Popen(cmd, shell=True)
            print(f"✅ Terminal ouvert pour {script_name}")
        
        return process
        
    except Exception as e:
        print(f"❌ Erreur lors du lancement de {script_name}: {e}")
        return None

def run_scripts_parallel():
    """
    Lance les scripts Disty et Disway en parallèle dans des terminaux séparés
    """
    print("🚀 LANCEUR DE SCRAPING PARALLÈLE")
    print("=" * 50)
    print(f"🕐 Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Chemins vers les scripts
    disty_script = "disty_script.py"
    disway_script = "disway_script.py"
    
    # Vérifier que les scripts existent
    if not os.path.exists(disty_script):
        print(f"❌ Script Disty introuvable: {disty_script}")
        return
    
    if not os.path.exists(disway_script):
        print(f"❌ Script Disway introuvable: {disway_script}")
        return
    
    print("📋 Scripts trouvés:")
    print(f"   • Disty: {disty_script}")
    print(f"   • Disway: {disway_script}")
    print()
    
    # Lancer les scripts dans des terminaux séparés
    print("🔄 Lancement des scripts...")
    print()
    
    disty_process = run_script_in_new_terminal(disty_script, "DISTY")
    time.sleep(2)  # Petit délai entre les lancements
    
    disway_process = run_script_in_new_terminal(disway_script, "DISWAY")
    
    print()
    print("✅ Les deux scripts ont été lancés dans des terminaux séparés")
    print()
    print("📋 INSTRUCTIONS:")
    print("   • Chaque script s'exécute dans son propre terminal")
    print("   • Vous pouvez suivre la progression dans chaque fenêtre")
    print("   • Les terminaux resteront ouverts à la fin de l'exécution")
    print("   • Fermez les fenêtres manuellement quand c'est terminé")
    print()
    print("⏳ Surveillance en cours... (Ctrl+C pour arrêter la surveillance)")
    
    try:
        # Surveiller pendant un moment
        while True:
            time.sleep(10)
            print("🔍 Surveillance active... Les scripts tournent en arrière-plan")
            
    except KeyboardInterrupt:
        print("\n⏹️  Surveillance arrêtée")
        print("📋 Les scripts continuent de tourner dans leurs terminaux")
        print("🕐 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def run_scripts_sequential():
    """
    Lance les scripts l'un après l'autre dans le même terminal (alternative)
    """
    print("🚀 LANCEUR DE SCRAPING SÉQUENTIEL")
    print("=" * 50)
    
    scripts = [
        ("DISTY", "disty_script.py"),
        ("DISWAY", "disway_script.py")
    ]
    
    for script_name, script_path in scripts:
        if not os.path.exists(script_path):
            print(f"❌ Script {script_name} introuvable: {script_path}")
            continue
            
        print(f"\n🎯 LANCEMENT DE {script_name}")
        print("=" * 30)
        
        try:
            # Exécuter le script dans le processus courant
            result = subprocess.run([sys.executable, script_path], 
                                 capture_output=False, 
                                 text=True)
            
            if result.returncode == 0:
                print(f"✅ {script_name} terminé avec succès")
            else:
                print(f"⚠️ {script_name} terminé avec des erreurs")
                
        except Exception as e:
            print(f"❌ Erreur lors de l'exécution de {script_name}: {e}")
        
        print(f"\n⏳ Pause avant le prochain script...")
        time.sleep(5)

def main():
    """
    Menu principal
    """
    print("🤖 LANCEUR AUTOMATIQUE DE SCRAPING")
    print("=" * 40)
    print("1. 🚀 Lancement parallèle (terminaux séparés)")
    print("2. 🔄 Lancement séquentiel (même terminal)")
    print("3. ❌ Quitter")
    print()
    
    while True:
        choice = input("Choisissez une option (1-3): ").strip()
        
        if choice == "1":
            run_scripts_parallel()
            break
        elif choice == "2":
            run_scripts_sequential()
            break
        elif choice == "3":
            print("👋 Au revoir!")
            break
        else:
            print("❌ Option invalide. Choisissez 1, 2 ou 3.")

if __name__ == "__main__":
    main()
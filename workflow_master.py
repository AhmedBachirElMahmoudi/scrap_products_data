"""
WORKFLOW MASTER - Automatisation complète du scraping et synchronisation
Lance tous les processus dans le bon ordre avec parallélisation
"""

import subprocess
import sys
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Configuration
PYTHON_CMD = sys.executable  # Utilise le même Python que celui qui exécute ce script

class WorkflowMaster:
    def __init__(self):
        self.start_time = None
        self.logs = []
        self.lock = threading.Lock()
        
    def log(self, message, level="INFO"):
        """Ajoute un message au log avec timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}"
        with self.lock:
            self.logs.append(log_msg)
            print(log_msg)
    
    def run_script(self, script_name, description):
        """
        Exécute un script Python et retourne le résultat
        """
        self.log(f"🚀 Démarrage: {description}", "INFO")
        start = time.time()
        
        try:
            result = subprocess.run(
                [PYTHON_CMD, script_name],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            elapsed = time.time() - start
            
            if result.returncode == 0:
                self.log(f"✅ Terminé: {description} ({elapsed:.1f}s)", "SUCCESS")
                return True, script_name, elapsed, result.stdout
            else:
                self.log(f"❌ Erreur: {description} ({elapsed:.1f}s)", "ERROR")
                self.log(f"   Détails: {result.stderr[:200]}", "ERROR")
                return False, script_name, elapsed, result.stderr
                
        except Exception as e:
            elapsed = time.time() - start
            self.log(f"❌ Exception: {description} - {str(e)}", "ERROR")
            return False, script_name, elapsed, str(e)
    
    def run_scripts_parallel(self, scripts, phase_name):
        """
        Exécute plusieurs scripts en parallèle
        scripts: liste de tuples (script_name, description)
        """
        self.log(f"\n{'='*60}", "INFO")
        self.log(f"📦 PHASE: {phase_name}", "INFO")
        self.log(f"   Nombre de scripts: {len(scripts)}", "INFO")
        self.log(f"{'='*60}\n", "INFO")
        
        results = []
        phase_start = time.time()
        
        with ThreadPoolExecutor(max_workers=len(scripts)) as executor:
            # Soumettre tous les scripts
            futures = {
                executor.submit(self.run_script, script, desc): (script, desc)
                for script, desc in scripts
            }
            
            # Attendre que tous se terminent
            for future in as_completed(futures):
                script, desc = futures[future]
                try:
                    success, name, elapsed, output = future.result()
                    results.append({
                        'script': name,
                        'description': desc,
                        'success': success,
                        'elapsed': elapsed,
                        'output': output
                    })
                except Exception as e:
                    self.log(f"❌ Erreur lors de l'exécution de {script}: {e}", "ERROR")
                    results.append({
                        'script': script,
                        'description': desc,
                        'success': False,
                        'elapsed': 0,
                        'output': str(e)
                    })
        
        phase_elapsed = time.time() - phase_start
        
        # Résumé de la phase
        successes = sum(1 for r in results if r['success'])
        failures = len(results) - successes
        
        self.log(f"\n{'='*60}", "INFO")
        self.log(f"📊 RÉSUMÉ {phase_name}:", "INFO")
        self.log(f"   ✅ Succès: {successes}/{len(results)}", "SUCCESS" if failures == 0 else "WARNING")
        self.log(f"   ❌ Échecs: {failures}/{len(results)}", "INFO" if failures == 0 else "ERROR")
        self.log(f"   ⏱️  Temps total: {phase_elapsed:.1f}s", "INFO")
        self.log(f"{'='*60}\n", "INFO")
        
        return results, successes == len(results)
    
    def run_script_sequential(self, script_name, description):
        """Exécute un script de manière séquentielle"""
        self.log(f"\n{'='*60}", "INFO")
        self.log(f"🎯 ÉTAPE: {description}", "INFO")
        self.log(f"{'='*60}\n", "INFO")
        
        success, name, elapsed, output = self.run_script(script_name, description)
        
        return success
    
    def run_full_workflow(self):
        """
        Exécute le workflow complet
        """
        self.start_time = datetime.now()
        
        print("\n" + "="*60)
        print("🚀 WORKFLOW MASTER - LANCEMENT COMPLET")
        print("="*60)
        print(f"🕐 Début: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        workflow_success = True
        
        # ========================================
        # PHASE 1: Scraping Disty & Disway (PARALLÈLE)
        # ========================================
        phase1_scripts = [
            ("disty_script.py", "Scraping DISTY"),
            ("disway_script.py", "Scraping DISWAY")
        ]
        
        results1, success1 = self.run_scripts_parallel(
            phase1_scripts, 
            "PHASE 1 - Scraping Disty & Disway"
        )
        
        if not success1:
            self.log("⚠️  PHASE 1 a des erreurs, mais on continue...", "WARNING")
            workflow_success = False
        
        # Pause entre les phases
        time.sleep(2)
        
        # ========================================
        # PHASE 2: Comparaison et calcul des prix DIX
        # ========================================
        success2 = self.run_script_sequential(
            "comparaison.py",
            "PHASE 2 - Comparaison et calcul des prix DIX"
        )
        
        if not success2:
            self.log("❌ PHASE 2 a échoué, arrêt du workflow", "ERROR")
            return False
        
        time.sleep(2)
        
        # ========================================
        # PHASE 3: Scraping des 7 sites concurrents (PARALLÈLE)
        # ========================================
        phase3_scripts = [
            ("crenova_scrap.py", "Scraping CRENOVA"),
            ("duga_scrap.py", "Scraping DUGA"),
            ("linksolutions_scrap.py", "Scraping LINKSOLUTIONS"),
            ("tabtel_scrap.py", "Scraping TABTEL"),
            ("mies_scrap.py", "Scraping MIES"),
            ("rightech_scrap.py", "Scraping RIGHTECH"),
            ("joutech_scrap.py", "Scraping JOUTECH")
        ]
        
        results3, success3 = self.run_scripts_parallel(
            phase3_scripts,
            "PHASE 3 - Scraping des 7 sites concurrents"
        )
        
        if not success3:
            self.log("⚠️  PHASE 3 a des erreurs, mais on continue...", "WARNING")
            workflow_success = False
        
        time.sleep(2)
        
        # ========================================
        # PHASE 4: Fusion des données
        # ========================================
        success4 = self.run_script_sequential(
            "merge_scraped_data.py",
            "PHASE 4 - Fusion des données (DIX + 7 concurrents)"
        )
        
        if not success4:
            self.log("❌ PHASE 4 a échoué, arrêt du workflow", "ERROR")
            return False
        
        time.sleep(2)
        
        # ========================================
        # PHASE 5: Synchronisation vers dix_temp
        # ========================================
        success5 = self.run_script_sequential(
            "sync_to_temp.py",
            "PHASE 5 - Synchronisation vers dix_temp"
        )
        
        if not success5:
            self.log("⚠️  PHASE 5 a échoué, mais on continue...", "WARNING")
            workflow_success = False
        
        time.sleep(2)
        
        # ========================================
        # PHASE 6: Synchronisation WordPress
        # ========================================
        success6 = self.run_script_sequential(
            "test.py",
            "PHASE 6 - Synchronisation WordPress (produits)"
        )
        
        if not success6:
            self.log("❌ PHASE 6 a échoué, arrêt du workflow", "ERROR")
            return False
        
        time.sleep(2)
        
        # ========================================
        # PHASE 7: Peupler et synchroniser les attributs
        # ========================================
        success7a = self.run_script_sequential(
            "populate_attributes.py",
            "PHASE 7a - Peupler les attributs manquants"
        )
        
        time.sleep(2)
        
        success7b = self.run_script_sequential(
            "sync_attributes.py",
            "PHASE 7b - Synchroniser les attributs vers WooCommerce"
        )
        
        if not (success7a and success7b):
            self.log("⚠️  PHASE 7 a des erreurs, mais on continue...", "WARNING")
            workflow_success = False
        
        time.sleep(2)
        
        # ========================================
        # PHASE 8: Mise à jour des catégories et marques
        # ========================================
        success8a = self.run_script_sequential(
            "update_categories.py",
            "PHASE 8a - Mise à jour des catégories"
        )
        
        if not success8a:
            self.log("⚠️  PHASE 8a a échoué, mais on continue...", "WARNING")
            workflow_success = False
        
        # ========================================
        # RÉSUMÉ FINAL
        # ========================================
        end_time = datetime.now()
        total_elapsed = (end_time - self.start_time).total_seconds()
        
        print("\n" + "="*60)
        print("🏁 WORKFLOW TERMINÉ")
        print("="*60)
        print(f"🕐 Début:  {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕐 Fin:    {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Durée:  {total_elapsed/60:.1f} minutes ({total_elapsed:.0f}s)")
        print(f"📊 Statut: {'✅ SUCCÈS' if workflow_success else '⚠️  AVEC ERREURS'}")
        print("="*60 + "\n")
        
        # Sauvegarder les logs
        self.save_logs()
        
        return workflow_success
    
    def save_logs(self):
        """Sauvegarde les logs dans un fichier"""
        log_filename = f"workflow_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(log_filename, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.logs))
            self.log(f"📝 Logs sauvegardés dans: {log_filename}", "INFO")
        except Exception as e:
            self.log(f"❌ Erreur lors de la sauvegarde des logs: {e}", "ERROR")


def main():
    """Point d'entrée principal"""
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║           🚀 WORKFLOW MASTER - DIX PLATFORM 🚀          ║
    ║                                                          ║
    ║  Ce script va exécuter automatiquement:                  ║
    ║  1. Scraping Disty & Disway (parallèle)                  ║
    ║  2. Comparaison et calcul des prix DIX                   ║
    ║  3. Scraping des 7 sites concurrents (parallèle)         ║
    ║  4. Fusion des données                                   ║
    ║  5. Synchronisation vers dix_temp                        ║
    ║  6. Synchronisation WordPress                            ║
    ║  7. Synchronisation des attributs                        ║
    ║  8. Mise à jour des catégories                           ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    response = input("Voulez-vous lancer le workflow complet ? (o/n): ").strip().lower()
    
    if response != 'o':
        print("❌ Workflow annulé par l'utilisateur")
        return
    
    print("\n🚀 Lancement du workflow...\n")
    
    workflow = WorkflowMaster()
    success = workflow.run_full_workflow()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

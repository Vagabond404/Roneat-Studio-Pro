<div align="center">
  <img src="assets/logo.png" alt="Roneat Studio Pro Logo" width="200" />
  
  <h1>Roneat Studio Pro ᨠ</h1>
  
  <p>
    <b>A professional suite designed for transcribing, editing, and exporting scores for the Roneat (the traditional Cambodian xylophone).</b>
  </p>
  <p>
    It combines modern AI audio analysis with a specialized score editor to bridge the gap between traditional performance and digital notation.
  </p>
</div>

<<<<<<< HEAD
![Version](https://img.shields.io/badge/version-2.0.1-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-Non--Commercial-red.svg)

**Roneat Studio Pro** est une suite logicielle professionnelle conçue pour la transcription, l'édition et l'exportation de partitions pour le **Roneat Ek** (le xylophone traditionnel cambodgien). Ce logiciel combine une analyse audio par intelligence artificielle avec un éditeur de partition 2D spécialisé, créant ainsi un pont entre la performance musicale traditionnelle et la notation numérique moderne.

![Roneat Studio Pro Logo](assets/logo.png)
=======
<br />
>>>>>>> 0423b09f14febcd19627d33bf61bbf31d0d3cccb

## 📋 Table des matières

- [Fonctionnalités Principales](#-fonctionnalités-principales)
- [Prérequis](#-prérequis)
- [Installation (Code Source)](#-installation-code-source)
- [Utilisation](#-utilisation)
- [Compilation (Créer l'exécutable)](#-compilation-créer-lexécutable)
- [Licence et Contact](#-licence-et-contact)

<<<<<<< HEAD
---
=======
<br />

## 🚀 Getting Started (For Developers & Source Code Users)

If you are running the software from the source code, follow these steps to set up your environment.
>>>>>>> 0423b09f14febcd19627d33bf61bbf31d0d3cccb

## ✨ Fonctionnalités Principales

- **🎼 Éditeur de Partition Professionnel** : Un éditeur 2D spécialement pensé pour la notation du Roneat. Intègre une visualisation fluide et une lecture en temps réel.
- **🎤 Transcription Audio par IA** : Convertissez vos enregistrements de Roneat directement en notation numérique grâce à une détection de hauteur (pitch) avancée et un système d'empreinte sonore.
- **⚖️ Calibration Avancée** : Affinez l'intelligence artificielle en enregistrant les propres "empreintes" sonores de votre instrument pour une précision de transcription quasi-parfaite.
- **📹 Export Vidéo MP4** : Générez des vidéos haute définition (2D) de vos partitions, parfaitement synchronisées avec l'audio. Idéal pour les réseaux sociaux, YouTube ou l'enseignement.
- **📄 Export PDF** : Exportez des partitions de haute qualité, prêtes à être imprimées et partagées.
- **📂 Gestion de Projet** : Sauvegardez, reprenez et gérez votre travail facilement grâce au format de projet natif `.roneat`.
- **🖱️ Glisser-Déposer (Drag & Drop)** : Importez rapidement des fichiers audio ou ouvrez vos projets en les glissant directement dans la fenêtre de l'application.

---

<<<<<<< HEAD
## 🚀 Prérequis

Pour exécuter le code source de Roneat Studio Pro sur votre machine, vous aurez besoin de :

- **Python 3.10 ou supérieur** : [Télécharger Python](https://www.python.org/downloads/)
- **FFmpeg** : Requis pour le traitement audio et le multiplexage de l'export vidéo MP4.

---
=======
**1. Clone the repository**:
```bash
git clone https://github.com/Vagabond404/Roneat-Studio-Pro.git
cd Roneat-Studio-Pro
```

**2. Create a Virtual Environment (Highly Recommended)**:
```bash
python -m venv .venv
```

**Activate the virtual environment**:

*On Windows*:
```bash
.\.venv\Scripts\activate
```

*On macOS/Linux*:
```bash
source .venv/bin/activate
```

**3. Install Dependencies**:
```bash
pip install -r requirements.txt
```

**4. Add FFmpeg**:
- Download `ffmpeg.exe` for your system.
- Place `ffmpeg.exe` directly in the root folder of the project (next to `main.py`).
>>>>>>> 0423b09f14febcd19627d33bf61bbf31d0d3cccb

## 🛠️ Installation (Code Source)

Si vous clonez ce dépôt pour exécuter ou modifier le logiciel, suivez ces étapes attentivement :

**1. Cloner le dépôt**
```bash
git clone https://github.com/Vagabond404/Roneat-Studio-Pro.git
cd Roneat-Studio-Pro
```

**2. Créer un environnement virtuel (Recommandé)**
```bash
python -m venv venv
# Sur Windows
.\venv\Scripts\activate
```

**3. Installer les dépendances**
```bash
pip install -r requirements.txt
```

**4. Ajouter FFmpeg**
- Téléchargez `ffmpeg.exe` pour Windows.
- Placez `ffmpeg.exe` directement à la racine du projet (à côté de `main.py`).

---

## 🚀 Utilisation

Pour lancer l'application :
```bash
python main.py
```

<<<<<<< HEAD
---
=======
<br />

## 🛠️ Building the Executable
>>>>>>> 0423b09f14febcd19627d33bf61bbf31d0d3cccb

## 🔄 Mise à jour GitHub

<<<<<<< HEAD
Pour envoyer rapidement vos modifications sur GitHub (add, commit et push en une seule fois) :

1. Lancez le script d'automatisation :
   ```bash
   python push_git.py "Votre message de commit"
   ```
Ce script est automatiquement exclu de l'exécutable final pour garder la distribution propre.

---

## 🛠️ Compilation (Créer l'exécutable)

Pour générer un fichier `.exe` autonome pour Windows :

1. Installez PyInstaller :
   ```bash
   python -m pip install pyinstaller
   ```
2. Lancez le script de build :
   ```bash
   python build.py
   ```
L'exécutable sera généré dans le dossier `dist/`.

---

## 📝 Licence et Contact

Ce logiciel est protégé par une **Licence Personnalisée Non-Commerciale**. Voir [LICENSE.txt](LICENSE.txt) pour le texte complet.

- **Auteur** : Ange Labbe
- **Email** : contact@angelvisionlabs.com

---
*Développé par Vagabond404 — 2026*
=======
**1. Install PyInstaller**:
```bash
pip install pyinstaller
```

**2. Run the build script**:
```bash
python build.py
```
*The executable will be generated in the `dist/` folder.*

<br />

## 📝 License

This project is governed by a Custom Non-Commercial License. You may modify the code, but you may not use this software or any of its derivatives to generate revenue without explicit authorization. See `LICENSE.txt` for full details.

---
*Developed by Ange Labbe — 2026*
>>>>>>> 0423b09f14febcd19627d33bf61bbf31d0d3cccb

"""
Splash Screen pour Strategy Price Monitor
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal as Signal, QPropertyAnimation, QEasingCurve, QPointF
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QPen, QBrush, QPixmap, QRadialGradient
import os
import random
import math


class SplashScreen(QWidget):
    """Splash screen animé avec logo"""
    
    finished = Signal()
    
    def __init__(self):
        super().__init__(None, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)  # type: ignore
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # type: ignore
        self.setFixedSize(700, 700)
        
        self._progress = 0
        self.coins = []  # Liste des pièces qui tombent
        self._setup_ui()
        self._center_on_screen()
        self._start_loading()
        self._start_coin_rain()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # Titre avec icône
        self.title_label = QLabel(" STRATEGY MONITOR")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore
        self.title_label.setStyleSheet("""
            QLabel {
                color: #00ff88;
                font-size: 32px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial;
                letter-spacing: 3px;
            }
        """)
        layout.addWidget(self.title_label)
        subtitle = QLabel("Real-Time Options Strategy Pricing")

        # Image Picsou
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        picsou_path = os.path.join(app_dir, "assets", "picsou.jpg")
        if os.path.exists(picsou_path):
            picsou_label = QLabel()
            pixmap = QPixmap(picsou_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)  # type: ignore
                picsou_label.setPixmap(pixmap)
                picsou_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore
                layout.addWidget(picsou_label)

        # Sous-titre
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore
        subtitle.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 14px;
                font-family: 'Segoe UI', Arial;
            }
        """)
        layout.addWidget(subtitle)
        
        layout.addSpacing(10)
        
        # Status de chargement
        self.status_label = QLabel("Initialisation...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #333;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00ff88, stop:0.5 #00aaff, stop:1 #00ff88);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Version
        version_label = QLabel("v1.0.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore
        version_label.setStyleSheet("""
            QLabel {
                color: #444;
                font-size: 10px;
            }
        """)
        layout.addWidget(version_label)
    
    def paintEvent(self, event):
        """Dessine le fond avec dégradé et les pièces"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # type: ignore
        
        # Fond avec dégradé
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(20, 20, 30))
        gradient.setColorAt(1, QColor(10, 10, 15))
        
        # Rectangle arrondi
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(0, 170, 255, 100), 2))
        painter.drawRoundedRect(10, 10, self.width() - 20, self.height() - 20, 15, 15)
        
        # Ligne décorative en haut
        painter.setPen(QPen(QColor(0, 255, 136), 3))
        painter.drawLine(30, 15, self.width() - 30, 15)
        
        # Dessiner les pièces qui tombent
        self._draw_coins(painter)
    
    def _draw_coins(self, painter):
        """Dessine des pièces 3D avec projection mathématique complète"""
        for coin in self.coins:
            painter.save()
            painter.translate(coin['x'], coin['y'])
            
            # Paramètres de la pièce (cylindre)
            radius = coin['size'] // 2
            thickness = 3
            angle = math.radians(coin['rotation'])
            
            # Projection 3D -> 2D (rotation autour de l'axe Y)
            # Pour un cylindre : x' = x*cos(α), z' = x*sin(α)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            # 1. Dessiner la tranche (bord du cylindre) si visible
            if abs(sin_a) > 0.1:  # Tranche visible
                painter.setBrush(QColor(180, 120, 0))
                painter.setPen(QPen(QColor(150, 100, 0), 1))
                
                # Points du contour de la tranche
                from PyQt6.QtCore import QPointF
                points = []
                for i in range(20):
                    theta = (i / 20) * 2 * math.pi
                    y = radius * math.sin(theta)
                    z = radius * math.cos(theta)
                    
                    # Projections des bords avant et arrière
                    x_front = thickness * sin_a
                    x_back = -thickness * sin_a
                    
                    # Ajouter les points du contour
                    if i in [0, 19]:  # Haut et bas
                        points.append(QPointF(x_back * cos_a, y))
                        points.append(QPointF(x_front * cos_a, y))
                
                # Dessiner la tranche comme un rectangle déformé
                edge_width = abs(2 * thickness * sin_a * cos_a)
                painter.drawRect(-edge_width/2, -radius, edge_width, 2*radius)
            
            # 2. Dessiner la face arrière (si visible)
            if cos_a < -0.05:
                painter.setBrush(QColor(200, 140, 0))
                painter.setPen(QPen(QColor(150, 100, 0), 2))
                x_offset = -thickness * sin_a
                width = int(2 * radius * abs(cos_a))
                painter.drawEllipse(x_offset - width/2, -radius, width, 2*radius)
            
            # 3. Dessiner la face avant (principale)
            if cos_a > -0.95:
                x_offset = thickness * sin_a
                width = int(2 * radius * abs(cos_a))
                
                # Cercle extérieur (bordure dorée foncée)
                outer_gradient = QRadialGradient(0, 0, radius)
                outer_gradient.setColorAt(0, QColor(220, 170, 20))  # Centre doré moyen
                outer_gradient.setColorAt(0.7, QColor(200, 140, 0))  # Dégradé vers foncé
                outer_gradient.setColorAt(1, QColor(160, 100, 0))   # Bordure très foncée
                painter.setBrush(QBrush(outer_gradient))
                painter.setPen(QPen(QColor(140, 90, 0), 2))
                painter.drawEllipse(x_offset - width/2, -radius, width, 2*radius)
                
                # Cercle intérieur (doré clair)
                inner_radius = int(radius * 0.75)
                inner_width = int(width * 0.75)
                inner_gradient = QRadialGradient(0, 0, inner_radius)
                inner_gradient.setColorAt(0, QColor(255, 240, 100))   # Centre très clair
                inner_gradient.setColorAt(0.5, QColor(255, 220, 60))  # Doré clair
                inner_gradient.setColorAt(1, QColor(240, 190, 30))    # Bordure claire
                painter.setBrush(QBrush(inner_gradient))
                painter.setPen(Qt.NoPen)  # type: ignore
                painter.drawEllipse(x_offset - inner_width/2, -inner_radius, inner_width, 2*inner_radius)
                
                # Symbole $ si face visible
                if abs(cos_a) > 0.3:
                    painter.setPen(QPen(QColor(140, 90, 0), 2))
                    font = QFont("Arial", max(8, int(radius * 0.8)), QFont.Bold)  # type: ignore
                    painter.setFont(font)
                    painter.drawText(-radius//2, radius//3, "$")
            
            painter.restore()
    
    def _center_on_screen(self):
        """Centre le splash screen"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def _start_loading(self):
        """Démarre l'animation de chargement"""
        self.loading_steps = [
            (10, "Chargement des modules..."),
            (25, "Initialisation de l'interface..."),
            (40, "Configuration du thème..."),
            (55, "Préparation du service Bloomberg..."),
            (70, "Chargement des stratégies..."),
            (85, "Finalisation..."),
            (100, "Prêt!")
        ]
        self.current_step = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(40)
    
    def _update_progress(self):
        """Met à jour la progression"""
        if self.current_step < len(self.loading_steps):
            progress, status = self.loading_steps[self.current_step]
            self.progress_bar.setValue(progress)
            self.status_label.setText(status)
            self.current_step += 1
        else:
            self.timer.stop()
            QTimer.singleShot(500, self._finish)
    
    def _finish(self):
        """Termine le splash screen"""
        if hasattr(self, 'coin_timer'):
            self.coin_timer.stop()
        self.finished.emit()
        self.close()
    
    def _start_coin_rain(self):
        """Démarre l'animation de pluie de pièces"""
        self.coin_timer = QTimer(self)
        self.coin_timer.timeout.connect(self._update_coins)
        self.coin_timer.start(30)  # 30ms = ~33 FPS
        
        # Timer pour ajouter de nouvelles pièces
        self.spawn_timer = QTimer(self)
        self.spawn_timer.timeout.connect(self._spawn_coin)
        self.spawn_timer.start(150)  # Nouvelle pièce toutes les 150ms
    
    def _spawn_coin(self):
        """Crée une nouvelle pièce"""
        coin = {
            'x': random.randint(0, self.width()),
            'y': -20,
            'vx': random.uniform(-1, 1),  # Vitesse horizontale
            'vy': random.uniform(2, 10),   # Vitesse verticale
            'rotation': random.uniform(0, 360),
            'rotation_speed': random.uniform(-10, 10),
            'size': random.randint(15, 50)
        }
        self.coins.append(coin)
    
    def _update_coins(self):
        """Met à jour la position des pièces"""
        # Mettre à jour chaque pièce
        for coin in self.coins[:]:
            coin['y'] += coin['vy']
            coin['x'] += coin['vx']
            coin['vy'] += 0.2  # Gravité
            coin['rotation'] += coin['rotation_speed']
            
            # Retirer les pièces hors écran
            if coin['y'] > self.height() + 200:
                self.coins.remove(coin)
        
        # Limiter le nombre de pièces
        if len(self.coins) > 150:
            self.coins = self.coins[-50:]
        
        self.update()  # Redessiner


def show_splash_and_run():
    """Affiche le splash screen puis lance l'app"""
    import sys
    from src.ui.main_window import MainWindow
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Configuration
    app.setApplicationName("Strategy Price Monitor")
    
    # Splash screen
    splash = SplashScreen()
    
    # Fenêtre principale (créée mais pas affichée)
    main_window = None
    
    def on_splash_finished():
        nonlocal main_window
        main_window = MainWindow()
        main_window.show()
    
    splash.finished.connect(on_splash_finished)
    splash.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    show_splash_and_run()

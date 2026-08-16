import React, { useState } from 'react';
import ServiceForm from './components/ServiceForm';
import TicketHistory from './components/TicketHistory';
import './styles.css';

// CORRECCIÓN: Extensión .png para que npm run build lo encuentre
import logoColor from './assets/Ocupasalud Logo a color.png';

type View = 'form' | 'history';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<View>('form');
  const [prefilledPatient, setPrefilledPatient] = useState<{ nombre: string; dni: string } | null>(null);

  const handleCargarPaciente = (nombre: string, dni: string) => {
    setPrefilledPatient({ nombre, dni });
    setCurrentView('form');
  };

  return (
    <div className="app-container">
      {/* Encabezado con Logo y Título en dos tonos */}
      <header className="app-header">
        <div className="logo-container">
          <img src={logoColor} alt="Ocupasalud Logo" />
        </div>
        <div className="header-title">
          <span className="title-top">Centro Médico Laboral</span>
          <span className="title-bottom">LAS MARIANAS</span>
        </div>
      </header>

      {/* --- Pestañas de Navegación --- */}
      <nav className="view-switcher">
        <button 
          onClick={() => setCurrentView('form')}
          className={currentView === 'form' ? 'active' : ''}
        >
          Generar Ticket
        </button>
        <button 
          onClick={() => setCurrentView('history')}
          className={currentView === 'history' ? 'active' : ''}
        >
          Ver Tickets Generados
        </button>
      </nav>

      <main className="app-main">
        {currentView === 'form' && <ServiceForm prefilledPatient={prefilledPatient} />}
        {currentView === 'history' && <TicketHistory onCargarPaciente={handleCargarPaciente} />}
      </main>
      
      <footer className="app-footer">
        <p>© 2026 Consultorio Las Marianas. Todos los derechos reservados.</p>
      </footer>
    </div>
  );
};

export default App;
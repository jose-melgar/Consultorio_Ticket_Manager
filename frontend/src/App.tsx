import React, { useState } from 'react';
import ServiceForm from './components/ServiceForm';
import TicketHistory from './components/TicketHistory'; // <-- Importamos el nuevo componente
import './styles.css';

type View = 'form' | 'history';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<View>('form');

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Consultorio Ticket Manager</h1>
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
        {/* Renderizado condicional basado en la vista actual */}
        {currentView === 'form' && <ServiceForm />}
        {currentView === 'history' && <TicketHistory />}
      </main>
      
      <footer className="app-footer">
        <p>© 2026 Consultorio Las Marianas. Todos los derechos reservados.</p>
      </footer>
    </div>
  );
};

export default App;
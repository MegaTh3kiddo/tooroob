import '../../styles/globals.css';
import { AppProvider } from '../../context/AppContext';
import { ModalContainer } from '../../components/modals/ModalContainer';

// Experimental React port of the UI (kept for reference; the main app at / runs the reference UI).
export default function ReactLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppProvider>
      {children}
      <ModalContainer />
    </AppProvider>
  );
}

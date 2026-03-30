import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

export default function TopBar() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const initials = user?.email ? user.email[0].toUpperCase() : '?';

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-border max-w-lg mx-auto">
      <h2 className="font-heading text-xl text-foreground cursor-pointer" onClick={() => navigate('/dashboard')}>
        SwingFit
      </h2>
      <button
        onClick={() => navigate('/profile')}
        className="w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-medium flex items-center justify-center"
      >
        {initials}
      </button>
    </header>
  );
}

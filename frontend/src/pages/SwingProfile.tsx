import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useQuery } from '@tanstack/react-query';
import { getSwingProfile } from '@/lib/api';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowRight } from 'lucide-react';
import BottomNav from '@/components/BottomNav';
import TopBar from '@/components/TopBar';
import { motion } from 'framer-motion';

function StatusDot({ status }: { status: 'green' | 'amber' | 'red' }) {
  const colors = { green: 'bg-emerald-500', amber: 'bg-amber-500', red: 'bg-red-500' };
  return <span className={`inline-block w-2 h-2 rounded-full ${colors[status]}`} />;
}

export default function SwingProfile() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const { data: profile, isLoading } = useQuery({
    queryKey: ['swingProfile', user?.id, 'driver'],
    queryFn: () => getSwingProfile('driver'),
    enabled: !!user,
    retry: false,
  });

  const hasDriver = profile !== null && profile !== undefined;

  const spinRate = profile?.avg_spin;
  const launchAngle = profile?.avg_launch;
  const clubSpeed = profile?.avg_club_speed;
  const ballSpeed = profile?.avg_ball_speed;
  const carry = profile?.avg_carry;

  const spinStatus = spinRate && spinRate > 2800 ? 'red' : spinRate && spinRate > 2500 ? 'amber' : 'green';
  const launchStatus = launchAngle && launchAngle > 14 ? 'amber' : 'green';

  return (
    <div className="min-h-screen pb-20">
      <TopBar />
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="px-6 py-8 max-w-lg mx-auto space-y-6"
      >
        <h1 className="font-heading text-2xl">Your Swing Profile</h1>

        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-64 w-full rounded-lg" />
          </div>
        ) : !hasDriver ? (
          <div className="bg-card border border-border rounded-lg p-8 text-center shadow-sm space-y-3">
            <p className="text-muted-foreground">No driver data yet. Upload a session to see your profile.</p>
          </div>
        ) : (
          <div className="bg-card border border-border rounded-lg shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <div>
                <h2 className="font-heading text-lg">DRIVER</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {profile.shot_count} shot{profile.shot_count !== 1 ? 's' : ''} · {profile.data_quality_tier || 'Standard'}
                </p>
              </div>
            </div>

            <div className="p-5 space-y-4">
              {[
                { label: 'Club Speed', value: clubSpeed ? `${clubSpeed.toFixed(1)} mph` : '—', status: 'green' as const },
                { label: 'Ball Speed', value: ballSpeed ? `${ballSpeed.toFixed(1)} mph` : '—', status: 'green' as const },
                { label: 'Launch Angle', value: launchAngle ? `${launchAngle.toFixed(1)}°` : '—', status: launchStatus as any },
                { label: 'Spin Rate', value: spinRate ? `${Math.round(spinRate).toLocaleString()} rpm` : '—', status: spinStatus as any },
                { label: 'Carry', value: carry ? `${carry.toFixed(0)} yd` : '—', status: 'green' as const },
              ].map((stat) => (
                <div key={stat.label} className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{stat.label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{stat.value}</span>
                    <StatusDot status={stat.status} />
                  </div>
                </div>
              ))}
            </div>

            {spinRate && spinRate > 2800 && (
              <div className="px-5 py-4 border-t border-border bg-muted/30">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  <span className="font-medium text-foreground">Insight:</span> Your spin rate is{' '}
                  {Math.round(spinRate - 2500)} rpm above the optimal window for your club speed.
                  A lower-spin driver head could add 8-15 yards of carry distance.
                </p>
              </div>
            )}

            <div className="px-5 py-4 border-t border-border">
              <button
                onClick={() => navigate('/shop')}
                className="text-sm text-primary font-medium flex items-center gap-1 hover:underline"
              >
                See Matched Clubs <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </motion.div>
      <BottomNav />
    </div>
  );
}

import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useQuery } from '@tanstack/react-query';
import { getSwingProfile, getRecommendations } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Upload, ArrowRight } from 'lucide-react';
import BottomNav from '@/components/BottomNav';
import TopBar from '@/components/TopBar';
import { motion } from 'framer-motion';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ['swingProfile', user?.id, 'driver'],
    queryFn: () => getSwingProfile('driver'),
    enabled: !!user,
    retry: false,
  });

  const { data: recsData, isLoading: recsLoading } = useQuery({
    queryKey: ['topPicks', user?.id],
    queryFn: () => getRecommendations({ club_type: 'driver', top_n: 3 }),
    enabled: !!user && !!profile,
    retry: false,
  });

  const isLoading = profileLoading || recsLoading;
  const hasData = profile !== null && profile !== undefined;
  const picks = recsData?.recommendations || [];

  return (
    <div className="min-h-screen pb-20">
      <TopBar />
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="px-6 py-8 max-w-lg mx-auto space-y-8"
      >
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-40 w-full rounded-lg" />
          </div>
        ) : hasData ? (
          <>
            {/* Swing Profile Summary */}
            <div className="bg-card border border-border rounded-lg p-6 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <h2 className="font-heading text-xl">Your Swing Profile</h2>
                <button
                  onClick={() => navigate('/swing-profile')}
                  className="text-sm text-primary flex items-center gap-1 hover:underline"
                >
                  View Details <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-2xl font-heading">{profile.avg_club_speed ? profile.avg_club_speed.toFixed(1) : '—'}</p>
                  <p className="text-xs text-muted-foreground mt-1">Club Speed</p>
                </div>
                <div>
                  <p className="text-2xl font-heading">{profile.avg_ball_speed ? profile.avg_ball_speed.toFixed(1) : '—'}</p>
                  <p className="text-xs text-muted-foreground mt-1">Ball Speed</p>
                </div>
                <div>
                  <p className="text-2xl font-heading">{profile.avg_carry ? profile.avg_carry.toFixed(0) : '—'}</p>
                  <p className="text-xs text-muted-foreground mt-1">Carry</p>
                </div>
              </div>
            </div>

            {/* Top Picks */}
            {picks.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-heading text-xl">Top Picks For You</h2>
                  <button
                    onClick={() => navigate('/shop')}
                    className="text-sm text-primary flex items-center gap-1 hover:underline"
                  >
                    See All <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="space-y-3">
                  {picks.map((rec: any) => {
                    const club = rec.club;
                    const displayName = `${club.brand} ${club.model_name}`;
                    return (
                      <div
                        key={club.id}
                        onClick={() => navigate('/shop')}
                        className="bg-card border border-border rounded-lg p-4 flex items-center justify-between shadow-sm cursor-pointer hover:shadow-md transition-shadow"
                      >
                        <div>
                          <p className="font-heading text-base">{displayName}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {club.loft ? `${club.loft}°` : ''} · {club.msrp ? `$${club.msrp}` : ''}
                          </p>
                        </div>
                        <span className="text-xs font-medium bg-accent/20 text-accent-foreground px-2.5 py-1 rounded-full">
                          {Math.round(rec.score)}%
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        ) : (
          /* Empty state */
          <div className="bg-card border border-border rounded-lg p-12 flex flex-col items-center text-center space-y-5 shadow-sm">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <Upload className="w-7 h-7 text-primary" />
            </div>
            <h2 className="font-heading text-2xl">Let's find your fit</h2>
            <p className="text-muted-foreground max-w-xs leading-relaxed">
              Upload your Trackman data to get personalized club recommendations.
            </p>
            <Button size="lg" onClick={() => navigate('/upload')}>
              Upload Session
            </Button>
          </div>
        )}
      </motion.div>
      <BottomNav />
    </div>
  );
}

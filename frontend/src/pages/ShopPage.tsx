import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useQuery } from '@tanstack/react-query';
import { getRecommendations } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Upload, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import BottomNav from '@/components/BottomNav';
import TopBar from '@/components/TopBar';
import { motion } from 'framer-motion';

export default function ShopPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [budget, setBudget] = useState([1000]);
  const [clubType, setClubType] = useState('driver');
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['recommendations', user?.id, clubType, budget[0]],
    queryFn: () => getRecommendations({
      club_type: clubType,
      budget_max: budget[0],
      include_used: true,
      top_n: 5,
    }),
    enabled: !!user,
    retry: false,
  });

  const recommendations = data?.recommendations || [];
  const hasData = data !== null && !error;
  const noProfile = error || data === null;

  return (
    <div className="min-h-screen pb-20">
      <TopBar />
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="px-6 py-8 max-w-lg mx-auto space-y-6"
      >
        {/* Banner */}
        <p className="text-xs text-muted-foreground text-center">
          Prices updated daily. Links may earn SwingFit a commission.
        </p>

        <div>
          <h1 className="font-heading text-2xl">Your Matches</h1>
          <p className="text-muted-foreground mt-1">Clubs matched to your swing, ranked by fit.</p>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-48 w-full rounded-lg" />
            ))}
          </div>
        ) : noProfile ? (
          <div className="bg-card border border-border rounded-lg p-12 flex flex-col items-center text-center space-y-5 shadow-sm">
            <Upload className="w-10 h-10 text-muted-foreground" />
            <h2 className="font-heading text-xl">No swing data yet</h2>
            <p className="text-muted-foreground text-sm max-w-xs">
              Your recommendations will appear here once you upload your first session.
            </p>
            <Button onClick={() => navigate('/upload')}>Upload Session</Button>
          </div>
        ) : (
          <>
            {/* Filters */}
            <div className="flex gap-4 items-end">
              <div className="flex-1 space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Club Type</label>
                <Select value={clubType} onValueChange={setClubType}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="driver">Driver</SelectItem>
                    <SelectItem value="3-wood">3-Wood</SelectItem>
                    <SelectItem value="5-iron">5-Iron</SelectItem>
                    <SelectItem value="7-iron">7-Iron</SelectItem>
                    <SelectItem value="PW">PW</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1 space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Budget: ${budget[0]}</label>
                <Slider value={budget} onValueChange={setBudget} min={0} max={1000} step={50} />
              </div>
            </div>

            {/* Product cards */}
            <div className="space-y-5">
              {recommendations.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-8">No clubs match your criteria. Try increasing your budget.</p>
              )}
              {recommendations.map((rec: any) => {
                const club = rec.club;
                const buyLinks = rec.buy_links || [];
                const newLink = buyLinks.find((l: any) => l.condition === 'new');
                const usedLink = buyLinks.find((l: any) => l.condition === 'used');
                const displayName = `${club.brand} ${club.model_name}`;
                return (
                  <motion.div
                    key={club.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-card border border-border rounded-lg shadow-sm hover:shadow-md transition-shadow overflow-hidden"
                  >
                    {/* Image placeholder */}
                    <div className="bg-muted h-36 flex items-center justify-center">
                      <span className="text-muted-foreground text-sm">Product Image</span>
                    </div>

                    <div className="p-5 space-y-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-heading text-lg">{displayName}</h3>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {club.loft ? `${club.loft}°` : ''} · {club.model_year || ''} · {club.spin_bias || ''}
                          </p>
                        </div>
                        <span className="text-xs font-semibold bg-accent/20 text-accent-foreground px-3 py-1 rounded-full whitespace-nowrap">
                          {Math.round(rec.score)}% Match
                        </span>
                      </div>

                      <p className="text-sm text-muted-foreground leading-relaxed">{rec.explanation}</p>

                      {/* Pricing rows */}
                      <div className="border-t border-border pt-3 space-y-2">
                        {club.msrp && (
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">New from ${club.msrp}</span>
                            {newLink && (
                              <a href={newLink.url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary font-medium flex items-center gap-1 hover:underline">
                                Buy <ExternalLink className="w-3 h-3" />
                              </a>
                            )}
                          </div>
                        )}
                        {club.avg_used_price && (
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">Used from ${club.avg_used_price}</span>
                            {usedLink && (
                              <a href={usedLink.url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary font-medium flex items-center gap-1 hover:underline">
                                Buy <ExternalLink className="w-3 h-3" />
                              </a>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Compare expandable */}
                      <button
                        onClick={() => setExpanded(expanded === displayName ? null : displayName)}
                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Compare to my current club
                        {expanded === displayName ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                      {expanded === displayName && (
                        <p className="text-xs text-muted-foreground bg-muted/50 p-3 rounded">
                          Upload more session data to see a head-to-head comparison with your current driver.
                        </p>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </>
        )}
      </motion.div>
      <BottomNav />
    </div>
  );
}

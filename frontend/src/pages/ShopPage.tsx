import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCachedRecommendations, generateRecommendations } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Upload, ExternalLink, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import BottomNav from '@/components/BottomNav';
import TopBar from '@/components/TopBar';
import { motion } from 'framer-motion';
import { toast } from 'sonner';

export default function ShopPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [budget, setBudget] = useState([1000]);
  const [clubType, setClubType] = useState('driver');
  const [expanded, setExpanded] = useState<string | null>(null);

  // Try cached recommendations first (fast, no API call)
  const { data: cachedData, isLoading } = useQuery({
    queryKey: ['cachedRecs', user?.id, clubType],
    queryFn: () => getCachedRecommendations(clubType),
    enabled: !!user,
    retry: false,
  });

  // Generate new recommendations (calls Claude API)
  const generateMutation = useMutation({
    mutationFn: () => generateRecommendations({
      club_type: clubType,
      budget_max: budget[0],
      include_used: true,
      top_n: 5,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cachedRecs', user?.id, clubType] });
      toast.success('Recommendations generated!');
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const recommendations = cachedData?.recommendations || [];
  const hasCache = cachedData !== null && cachedData !== undefined;
  const filtered = recommendations.filter((rec: any) => {
    if (!rec.club) return false;
    const price = rec.club.avg_used_price || rec.club.msrp;
    return !price || price <= budget[0];
  });

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
        ) : generateMutation.isPending ? (
          <div className="bg-card border border-border rounded-lg p-12 flex flex-col items-center text-center space-y-5 shadow-sm">
            <div className="animate-pulse">
              <Sparkles className="w-10 h-10 text-primary" />
            </div>
            <h2 className="font-heading text-xl">Finding your perfect clubs...</h2>
            <p className="text-muted-foreground text-sm max-w-xs">
              Our fitting engine is analyzing your swing data against our club database.
            </p>
          </div>
        ) : !hasCache ? (
          <div className="bg-card border border-border rounded-lg p-12 flex flex-col items-center text-center space-y-5 shadow-sm">
            <Upload className="w-10 h-10 text-muted-foreground" />
            <h2 className="font-heading text-xl">Ready to find your fit</h2>
            <p className="text-muted-foreground text-sm max-w-xs">
              Upload swing data first, then generate personalized recommendations.
            </p>
            <div className="flex gap-3">
              <Button onClick={() => navigate('/upload')}>Upload Session</Button>
              <Button variant="outline" onClick={() => generateMutation.mutate()}>
                <Sparkles className="w-4 h-4 mr-2" />Generate Recommendations
              </Button>
            </div>
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

            {/* Regenerate button */}
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
              >
                <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                Refresh Recommendations
              </Button>
            </div>

            {/* Product cards */}
            <div className="space-y-5">
              {filtered.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-8">No clubs match your criteria. Try increasing your budget.</p>
              )}
              {filtered.map((rec: any) => {
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
                            {club.loft ? `${club.loft}\u00B0` : ''} · {club.model_year || ''} · {club.spin_bias || ''}
                          </p>
                        </div>
                        <span className="text-xs font-semibold bg-accent/20 text-accent-foreground px-3 py-1 rounded-full whitespace-nowrap">
                          {Math.round(rec.score)}% Match
                        </span>
                      </div>

                      <p className="text-sm text-muted-foreground leading-relaxed">{rec.explanation}</p>

                      {rec.best_for && (
                        <p className="text-xs font-medium text-primary">Best for: {rec.best_for}</p>
                      )}

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

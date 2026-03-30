import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import BottomNav from '@/components/BottomNav';
import TopBar from '@/components/TopBar';
import { motion } from 'framer-motion';
import { format } from 'date-fns';

export default function ProfilePage() {
  const { user, signOut } = useAuth();
  const queryClient = useQueryClient();

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ['profile', user?.id],
    queryFn: async () => {
      const { data, error } = await supabase.from('profiles').select('*').eq('id', user!.id).single();
      if (error) throw error;
      return data;
    },
    enabled: !!user,
  });

  const { data: sessions } = useQuery({
    queryKey: ['sessions', user?.id],
    queryFn: async () => {
      const { data, error } = await supabase.from('swing_sessions').select('*').order('created_at', { ascending: false });
      if (error) throw error;
      return data;
    },
    enabled: !!user,
  });

  const [displayName, setDisplayName] = useState('');
  const [handicap, setHandicap] = useState('');
  const [budgetMax, setBudgetMax] = useState([500]);
  const [includeUsed, setIncludeUsed] = useState(true);

  useEffect(() => {
    if (profile) {
      setDisplayName(profile.display_name || '');
      setHandicap(profile.handicap?.toString() || '');
      setBudgetMax([profile.budget_max || 500]);
      setIncludeUsed(profile.include_used ?? true);
    }
  }, [profile]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const { error } = await supabase.from('profiles').update({
        display_name: displayName,
        handicap: handicap ? parseFloat(handicap) : null,
        budget_max: budgetMax[0],
        include_used: includeUsed,
        updated_at: new Date().toISOString(),
      }).eq('id', user!.id);
      if (error) throw error;
    },
    onSuccess: () => {
      toast.success('Profile saved!');
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
    onError: (err: any) => toast.error(err.message),
  });

  return (
    <div className="min-h-screen pb-20">
      <TopBar />
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="px-6 py-8 max-w-lg mx-auto space-y-8"
      >
        <h1 className="font-heading text-2xl">Profile</h1>

        {profileLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="text-sm text-muted-foreground">{user?.email}</div>

            <div className="space-y-2">
              <Label>Display Name</Label>
              <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Your name" />
            </div>

            <div className="space-y-2">
              <Label>Handicap</Label>
              <Input type="number" value={handicap} onChange={(e) => setHandicap(e.target.value)} placeholder="e.g. 12" />
            </div>

            <div className="space-y-2">
              <Label>Budget per club: ${budgetMax[0]}</Label>
              <Slider value={budgetMax} onValueChange={setBudgetMax} min={0} max={1000} step={50} />
            </div>

            <div className="flex items-center justify-between">
              <Label>Include used clubs in recommendations</Label>
              <Switch checked={includeUsed} onCheckedChange={setIncludeUsed} />
            </div>

            <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending} className="w-full">
              {saveMutation.isPending ? 'Saving…' : 'Save Profile'}
            </Button>
          </div>
        )}

        {/* My Sessions */}
        <div className="space-y-3">
          <h2 className="font-heading text-xl">My Sessions</h2>
          {sessions && sessions.length > 0 ? (
            sessions.map((s) => (
              <div key={s.id} className="bg-card border border-border rounded-lg p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{s.club_used}</p>
                    <p className="text-xs text-muted-foreground">{s.launch_monitor_type} · {format(new Date(s.created_at), 'MMM d, yyyy')}</p>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">No sessions yet. Upload your first one to get started!</p>
          )}
        </div>

        <Button variant="outline" className="w-full" onClick={signOut}>
          Sign Out
        </Button>
      </motion.div>
      <BottomNav />
    </div>
  );
}

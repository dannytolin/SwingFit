import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { uploadTrackmanReport, uploadSessionFile, manualEntry } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Camera, FileText, Keyboard, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import BottomNav from '@/components/BottomNav';
import TopBar from '@/components/TopBar';
import { motion } from 'framer-motion';

const clubTypes = ['Driver', '3-Wood', '5-Wood', '3-Iron', '4-Iron', '5-Iron', '6-Iron', '7-Iron', '8-Iron', '9-Iron', 'PW', 'SW', 'LW'];

export default function UploadPage() {
  const { user } = useAuth();
  const [mode, setMode] = useState<'pick' | 'image' | 'csv' | 'manual'>('pick');
  const [saving, setSaving] = useState(false);
  const [imageLoading, setImageLoading] = useState(false);
  const [csvResult, setCsvResult] = useState<{ shot_count: number; session_id: number } | null>(null);

  const [form, setForm] = useState({
    club_used: 'Driver',
    club_speed: '',
    ball_speed: '',
    launch_angle: '',
    spin_rate: '',
    carry_distance: '',
  });

  const updateField = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];
    setImageLoading(true);
    setMode('image');
    try {
      const result = await uploadTrackmanReport(file);
      // Pre-fill form from the extracted data if available
      const extracted = result.extracted_data;
      if (extracted?.shots?.length) {
        const shot = extracted.shots[0];
        setForm({
          club_used: shot.club_used || 'Driver',
          club_speed: shot.club_speed != null ? String(shot.club_speed) : '',
          ball_speed: shot.ball_speed != null ? String(shot.ball_speed) : '',
          launch_angle: shot.launch_angle != null ? String(shot.launch_angle) : '',
          spin_rate: shot.spin_rate != null ? String(shot.spin_rate) : '',
          carry_distance: shot.carry_distance != null ? String(shot.carry_distance) : '',
        });
      }
      if (result.low_confidence_warning) {
        toast.warning('Low confidence reading — please review the numbers.');
      }
      toast.success(`Saved ${result.shot_count} shot(s) from report`);
    } catch (err: any) {
      toast.error(err.message);
      setMode('pick');
    } finally {
      setImageLoading(false);
    }
  };

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];
    setMode('csv');
    try {
      const result = await uploadSessionFile(file);
      setCsvResult({ shot_count: result.shot_count, session_id: result.session.id });
    } catch (err: any) {
      toast.error(err.message);
      setMode('pick');
    }
  };

  const handleSave = async () => {
    if (!user) return;
    setSaving(true);
    try {
      await manualEntry({
        club_type: form.club_used,
        club_speed: form.club_speed ? parseFloat(form.club_speed) : undefined,
        ball_speed: parseFloat(form.ball_speed),
        launch_angle: parseFloat(form.launch_angle),
        spin_rate: parseFloat(form.spin_rate),
        carry_distance: parseFloat(form.carry_distance),
      });
      toast.success('Session saved successfully!');
      setMode('pick');
      setForm({ club_used: 'Driver', club_speed: '', ball_speed: '', launch_angle: '', spin_rate: '', carry_distance: '' });
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen pb-20">
      <TopBar />
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="px-6 py-8 max-w-lg mx-auto space-y-6"
      >
        <div>
          <h1 className="font-heading text-2xl">Add Your Data</h1>
          <p className="text-muted-foreground mt-1">The more data you give us, the better your recommendations get.</p>
        </div>

        {mode === 'pick' && (
          <div className="space-y-4">
            {/* Image card */}
            <label className="block bg-card border border-border rounded-lg p-6 space-y-2 shadow-sm cursor-pointer hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3">
                <Camera className="w-5 h-5 text-primary" />
                <h3 className="font-heading text-lg">Snap Your Trackman Screen</h3>
              </div>
              <p className="text-sm text-muted-foreground">Take a screenshot of your Trackman app or photo of the screen. We'll read the numbers automatically.</p>
              <input type="file" accept="image/*,.pdf" className="hidden" onChange={handleImageUpload} />
            </label>

            {/* CSV card */}
            <label className="block bg-card border border-border rounded-lg p-6 space-y-2 shadow-sm cursor-pointer hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-primary" />
                <h3 className="font-heading text-lg">Upload a File</h3>
              </div>
              <p className="text-sm text-muted-foreground">Drop your CSV export from Trackman, Garmin, or any launch monitor.</p>
              <input type="file" accept=".csv" className="hidden" onChange={handleCsvUpload} />
            </label>

            {/* Manual card */}
            <button
              onClick={() => setMode('manual')}
              className="w-full text-left bg-card border border-border rounded-lg p-6 space-y-2 shadow-sm cursor-pointer hover:shadow-md transition-shadow"
            >
              <div className="flex items-center gap-3">
                <Keyboard className="w-5 h-5 text-primary" />
                <h3 className="font-heading text-lg">Type Your Numbers</h3>
              </div>
              <p className="text-sm text-muted-foreground">Know your averages? Enter them manually.</p>
            </button>
          </div>
        )}

        {/* Image mode — loading then form */}
        {mode === 'image' && (
          <div className="space-y-6">
            {imageLoading ? (
              <div className="bg-card border border-border rounded-lg p-10 text-center shadow-sm">
                <div className="animate-pulse space-y-3">
                  <Camera className="w-8 h-8 text-muted-foreground mx-auto" />
                  <p className="text-muted-foreground">Reading your data…</p>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 text-sm text-primary">
                  <CheckCircle2 className="w-4 h-4" />
                  <span className="font-medium">Data extracted — review below</span>
                </div>
                <DataForm form={form} updateField={updateField} />
                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setMode('pick')} className="flex-1">Done</Button>
                </div>
              </>
            )}
          </div>
        )}

        {/* CSV mode */}
        {mode === 'csv' && (
          <div className="bg-card border border-border rounded-lg p-6 space-y-4 shadow-sm">
            {csvResult ? (
              <>
                <div className="flex items-center gap-2 text-primary">
                  <CheckCircle2 className="w-5 h-5" />
                  <p className="font-medium">Imported {csvResult.shot_count} shots</p>
                </div>
                <p className="text-sm text-muted-foreground">Session #{csvResult.session_id} created.</p>
                <div className="flex gap-3">
                  <Button onClick={() => { setMode('pick'); setCsvResult(null); }}>Upload Another</Button>
                  <Button variant="outline" onClick={() => { setMode('pick'); setCsvResult(null); }}>Done</Button>
                </div>
              </>
            ) : (
              <div className="animate-pulse text-center py-4">
                <p className="text-muted-foreground">Processing file…</p>
              </div>
            )}
          </div>
        )}

        {/* Manual mode */}
        {mode === 'manual' && (
          <div className="space-y-6">
            <DataForm form={form} updateField={updateField} />
            <div className="flex gap-3">
              <Button onClick={handleSave} disabled={saving} className="flex-1">
                {saving ? 'Saving…' : 'Save Session'}
              </Button>
              <Button variant="outline" onClick={() => setMode('pick')}>Cancel</Button>
            </div>
          </div>
        )}
      </motion.div>
      <BottomNav />
    </div>
  );
}

function DataForm({ form, updateField }: { form: Record<string, string>; updateField: (k: string, v: string) => void }) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Club Type</Label>
        <Select value={form.club_used} onValueChange={(v) => updateField('club_used', v)}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {clubTypes.map((c) => (
              <SelectItem key={c} value={c}>{c}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {[
        { key: 'club_speed', label: 'Club Speed (mph)' },
        { key: 'ball_speed', label: 'Ball Speed (mph)' },
        { key: 'launch_angle', label: 'Launch Angle (°)' },
        { key: 'spin_rate', label: 'Spin Rate (rpm)' },
        { key: 'carry_distance', label: 'Carry Distance (yd)' },
      ].map((f) => (
        <div key={f.key} className="space-y-2">
          <Label>{f.label}</Label>
          <Input
            type="number"
            step="0.1"
            value={form[f.key]}
            onChange={(e) => updateField(f.key, e.target.value)}
            placeholder="—"
          />
        </div>
      ))}
    </div>
  );
}

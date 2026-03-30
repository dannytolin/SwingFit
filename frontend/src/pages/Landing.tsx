import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Camera, BarChart3, ShoppingBag } from 'lucide-react';
import { motion } from 'framer-motion';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.15, duration: 0.5 },
  }),
};

const steps = [
  { num: '01', title: 'Upload', desc: 'Drop your Trackman screenshot, CSV, or type your numbers.' },
  { num: '02', title: 'Analyze', desc: 'Our engine matches your swing data against hundreds of club models.' },
  { num: '03', title: 'Shop', desc: 'See pricing from top retailers and buy with confidence.' },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <header className="flex items-center justify-between px-6 md:px-12 py-5 max-w-6xl mx-auto w-full">
        <h2 className="font-heading text-2xl text-foreground">SwingFit</h2>
        <Button variant="ghost" size="sm" onClick={() => navigate('/auth')}>
          Sign In
        </Button>
      </header>

      {/* Hero */}
      <main className="flex-1">
        <motion.section
          initial="hidden"
          animate="visible"
          className="px-6 md:px-12 pt-16 pb-20 max-w-3xl mx-auto text-center"
        >
          <motion.h1
            variants={fadeUp}
            custom={0}
            className="text-4xl md:text-6xl font-heading leading-tight"
          >
            Your Swing.{' '}
            <span className="text-primary">Your Clubs.</span>
          </motion.h1>
          <motion.p
            variants={fadeUp}
            custom={1}
            className="text-muted-foreground text-lg md:text-xl mt-6 max-w-xl mx-auto leading-relaxed"
          >
            Upload your Trackman data and discover exactly which clubs are built for the way you swing.
          </motion.p>
          <motion.div variants={fadeUp} custom={2} className="mt-8">
            <Button
              size="lg"
              className="text-base px-10 py-6 rounded-lg"
              onClick={() => navigate('/auth')}
            >
              Find Your Fit
            </Button>
          </motion.div>
        </motion.section>

        <div className="border-t border-border" />

        {/* Features — editorial layout */}
        <section className="px-6 md:px-12 py-20 max-w-5xl mx-auto">
          <div className="grid md:grid-cols-3 gap-12 md:gap-16">
            {[
              {
                icon: Camera,
                title: 'Upload Your Session',
                desc: 'Snap a photo of your Trackman screen, drop a CSV export, or type your averages. We handle the rest.',
              },
              {
                icon: BarChart3,
                title: 'Personalized Matches',
                desc: 'Our fitting engine analyzes your swing metrics against hundreds of club models to find your ideal specs.',
              },
              {
                icon: ShoppingBag,
                title: 'Shop With Confidence',
                desc: 'See new and used pricing from top retailers with direct links. Buy the right club at the right price.',
              },
            ].map((f, i) => (
              <motion.div
                key={f.title}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeUp}
                custom={i}
                className="space-y-4"
              >
                <div className="w-11 h-11 rounded-lg bg-primary/10 flex items-center justify-center">
                  <f.icon className="w-5 h-5 text-primary" />
                </div>
                <h3 className="font-heading text-xl">{f.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </section>

        <div className="border-t border-border" />

        {/* How It Works */}
        <section className="px-6 md:px-12 py-20 max-w-5xl mx-auto">
          <h2 className="font-heading text-3xl text-center mb-14">How It Works</h2>
          <div className="grid md:grid-cols-3 gap-10">
            {steps.map((s, i) => (
              <motion.div
                key={s.num}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeUp}
                custom={i}
                className="text-center md:text-left"
              >
                <span className="text-accent font-body font-bold text-sm tracking-widest">{s.num}</span>
                <h3 className="font-heading text-2xl mt-2">{s.title}</h3>
                <p className="text-muted-foreground mt-3 leading-relaxed">{s.desc}</p>
              </motion.div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border text-center text-xs text-muted-foreground py-8">
        © 2026 SwingFit. All rights reserved.
      </footer>
    </div>
  );
}

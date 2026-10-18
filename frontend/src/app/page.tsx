import Link from "next/link";
import HotSauceHero from "@/components/HotSauceHero";
import { ClipboardCheck, ScanText, TriangleAlert, History, Check } from "lucide-react";

const checks = [
  "Compare against approved specs",
  "Find mismatches and missing info",
  "Keep inspection records",
];

const features = [
  { title: "Reference", text: "Compare against your saved product specifications.", icon: ClipboardCheck },
  { title: "Detection", text: "Extract readable text from uploaded label images.", icon: ScanText },
  { title: "Review", text: "Flag differences and uncertain text for attention.", icon: TriangleAlert },
  { title: "Traceability", text: "Revisit saved inspection results when available.", icon: History },
];

export default function Home() {
  return <div className="landing-page">
    <section id="product" className="landing-hero">
      <div className="hero-copy">
        <p className="hero-eyebrow">AI PRODUCT LABEL VERIFICATION</p>
        <h1><span className="headline-lead">Catch label mistakes</span><span className="headline-followup">before your next production run.</span></h1>
        <p className="hero-description">One wrong label can mean wasted packaging, costly reprints, and delayed shipments. VeriLabel compares photographed product labels with your approved specifications, highlighting differences and unreadable fields so your team knows what needs attention.</p>
        <div className="hero-actions"><Link href="/inspect?demo=1" className="primary-button">Try a Sample Inspection <span aria-hidden="true">→</span></Link><Link href="/specs?new=1" className="outline-button">Create a Specification</Link></div>
        <p className="hero-demo-note">Runs a real check on a sample label with a wrong net weight.</p>
        <ul className="hero-checks">{checks.map(c=><li key={c}><Check size={16} strokeWidth={2} aria-hidden="true" />{c}</li>)}</ul>
      </div>
      <div className="hero-visual">
        <div className="hero-hexagon" aria-hidden="true" />
        <HotSauceHero />
      </div>
    </section>
    <section id="solutions" className="landing-features">
      <h2>Built for the checks your team already makes</h2>
      <div className="feature-grid">{features.map(f=><article key={f.title}><span className="feature-icon"><f.icon size={24} strokeWidth={1.75} aria-hidden="true" /></span><div><h3>{f.title}</h3><p>{f.text}</p></div></article>)}</div>
    </section>
  </div>;
}

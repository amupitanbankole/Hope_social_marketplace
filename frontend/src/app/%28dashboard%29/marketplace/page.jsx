"use client";

import { useMemo, useState, useEffect, createElement } from "react";
import {
  Search, Filter, Sparkles, Zap, ShieldCheck, CheckCircle2, CreditCard,
  Building2, Smartphone, Wallet, Lock, Copy, Check, ShoppingBag, ArrowRight,
  Minus, Plus, ExternalLink, Package, Wrench
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
  Pagination, PaginationContent, PaginationItem, PaginationLink,
  PaginationNext, PaginationPrevious,
} from "@/components/ui/pagination";
import { platforms, platformIcons } from "@/data/mock";
import { placeOrder, getPaymentConfig, getUserProfile, getServices } from "@/lib/api";
import { toast } from "sonner";

const platformStyles = {
  Instagram: { badgeBg: "bg-pink-500/15 text-pink-400 border-pink-500/30", iconBg: "bg-gradient-to-tr from-amber-500 via-pink-500 to-purple-600 text-white", activePill: "bg-pink-500 text-white" },
  TikTok: { badgeBg: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30", iconBg: "bg-gradient-to-tr from-cyan-500 to-pink-500 text-black font-bold", activePill: "bg-cyan-500 text-black font-semibold" },
  YouTube: { badgeBg: "bg-red-500/15 text-red-400 border-red-500/30", iconBg: "bg-red-600 text-white", activePill: "bg-red-600 text-white" },
  "Twitter/X": { badgeBg: "bg-slate-500/15 text-slate-300 border-slate-500/30", iconBg: "bg-slate-800 text-white border border-slate-700", activePill: "bg-slate-700 text-white" },
  Telegram: { badgeBg: "bg-sky-500/15 text-sky-400 border-sky-500/30", iconBg: "bg-sky-500 text-white", activePill: "bg-sky-500 text-white" },
  Discord: { badgeBg: "bg-indigo-500/15 text-indigo-400 border-indigo-500/30", iconBg: "bg-indigo-600 text-white", activePill: "bg-indigo-600 text-white" },
  LinkedIn: { badgeBg: "bg-blue-500/15 text-blue-400 border-blue-500/30", iconBg: "bg-blue-600 text-white", activePill: "bg-blue-600 text-white" },
  Snapchat: { badgeBg: "bg-amber-400/15 text-amber-300 border-amber-400/30", iconBg: "bg-amber-400 text-black font-bold", activePill: "bg-amber-400 text-black font-semibold" },
  Pinterest: { badgeBg: "bg-rose-500/15 text-rose-400 border-rose-500/30", iconBg: "bg-rose-600 text-white", activePill: "bg-rose-600 text-white" },
  Facebook: { badgeBg: "bg-blue-600/15 text-blue-400 border-blue-600/30", iconBg: "bg-blue-600 text-white", activePill: "bg-blue-600 text-white" },
};

const normalizeListingType = (item) => String(item?.listing_type || item?.listingType || "service").toLowerCase() === "product" ? "product" : "service";

const getItemPrice = (item) => Number.parseFloat(item?.rate_per_1k ?? item?.price ?? item?.rate ?? item?.amount ?? 0) || 0;

export default function Marketplace() {
  const [q, setQ] = useState("");
  const [platform, setPlatform] = useState("all");
  const [category, setCategory] = useState("all");
  const [listingType, setListingType] = useState("all");
  const [sort, setSort] = useState("popular");
  const [page, setPage] = useState(1);
  const perPage = 12;

  const [selectedItem, setSelectedItem] = useState(null);
  const [orderQuantity, setOrderQuantity] = useState(1);
  const [targetLink, setTargetLink] = useState("");
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [checkoutItem, setCheckoutItem] = useState(null);
  const [copiedRef, setCopiedRef] = useState(false);
  const [copiedAccount, setCopiedAccount] = useState(false);
  const [paymentConfig, setPaymentConfig] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [dbServices, setDbServices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([getPaymentConfig(), getUserProfile(), getServices()]).then(([payment, profile, catalog]) => {
      if (payment.status === "fulfilled" && payment.value) setPaymentConfig(payment.value);
      if (profile.status === "fulfilled" && profile.value) setUserProfile(profile.value);
      if (catalog.status === "fulfilled") {
        const list = Array.isArray(catalog.value) ? catalog.value : (catalog.value?.results || catalog.value?.data || []);
        setDbServices(Array.isArray(list) ? list : []);
      }
    }).finally(() => setLoading(false));
  }, []);

  const bankName = paymentConfig?.bank_name || process.env.NEXT_PUBLIC_BANK_NAME || "Moniepoint / GTBank";
  const accountName = paymentConfig?.account_name || process.env.NEXT_PUBLIC_ACCOUNT_NAME || "HopeSocial Ltd";
  const accountNumber = paymentConfig?.account_number || process.env.NEXT_PUBLIC_ACCOUNT_NUMBER || "2034829102";

  const categories = useMemo(() => {
    const values = dbServices.map((item) => item?.category).filter(Boolean).map(String);
    return [...new Set(values)].sort((a, b) => a.localeCompare(b));
  }, [dbServices]);

  const filtered = useMemo(() => {
    let items = dbServices.filter((item) => {
      const itemPlatform = String(item?.platform || "").toLowerCase();
      const text = `${item?.name || ""} ${item?.category || ""} ${item?.platform || ""} ${item?.description || ""}`.toLowerCase();
      return (
        (platform === "all" || itemPlatform === platform.toLowerCase()) &&
        (category === "all" || String(item?.category || "") === category) &&
        (listingType === "all" || normalizeListingType(item) === listingType) &&
        (!q.trim() || text.includes(q.trim().toLowerCase()))
      );
    });

    if (sort === "price-asc") items = [...items].sort((a, b) => getItemPrice(a) - getItemPrice(b));
    if (sort === "price-desc") items = [...items].sort((a, b) => getItemPrice(b) - getItemPrice(a));
    return items;
  }, [dbServices, q, platform, category, listingType, sort]);

  useEffect(() => setPage(1), [q, platform, category, listingType, sort]);

  const pages = Math.max(1, Math.ceil(filtered.length / perPage));
  const paged = filtered.slice((page - 1) * perPage, page * perPage);

  const openOrderModal = (item) => {
    const isAvailable = item?.is_active !== false && item?.isActive !== false && item?.in_stock !== false && item?.inStock !== false;
    if (!isAvailable) {
      toast.error(`'${item?.name}' is currently unavailable.`);
      return;
    }

    const type = normalizeListingType(item);
    const min = Number(item?.min_order ?? item?.min ?? 1) || 1;
    setSelectedItem(item);
    setOrderQuantity(type === "product" ? 1 : min);
    setTargetLink(type === "product" ? "" : `https://${String(item?.platform || "social").toLowerCase().replace(/[^a-z0-9]/g, "")}.com/your_profile`);
  };

  const handleProceedToPayment = () => {
    if (!selectedItem) return;
    const type = normalizeListingType(selectedItem);
    if (type === "service" && !targetLink.trim()) {
      toast.error("Please enter your target profile or post link");
      return;
    }

    const rate = getItemPrice(selectedItem);
    const totalAmount = type === "service" ? (orderQuantity / 1000) * rate : orderQuantity * rate;
    const refCode = `HS-MKT-${Math.floor(100000 + Math.random() * 900000)}`;

    setCheckoutItem({
      title: selectedItem.name,
      serviceId: selectedItem.id,
      providerServiceId: selectedItem.provider_service_id,
      listingType: type,
      platform: selectedItem.platform,
      quantity: orderQuantity,
      targetLink: targetLink || "Direct Product Purchase",
      unitRate: rate,
      totalAmount,
      reference: refCode,
      externalUrl: selectedItem.external_url || "",
    });
    setSelectedItem(null);
    setIsPaymentModalOpen(true);
  };

  const handleCompletePayment = async (methodName) => {
    try {
      if (checkoutItem) {
        await placeOrder({
          service: checkoutItem.serviceId,
          quantity: checkoutItem.quantity,
          target_link: checkoutItem.targetLink,
          payment_method: methodName,
          marketplace_listing_type: checkoutItem.listingType,
          provider_service_id: checkoutItem.providerServiceId,
        });
      }
      toast.success(`Order for '${checkoutItem?.title}' placed via ${methodName}!`, {
        description: `Reference #${checkoutItem?.reference}`,
      });
    } catch (err) {
      toast.error(err.message || "Failed to place order.");
    } finally {
      setIsPaymentModalOpen(false);
      setCheckoutItem(null);
    }
  };

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text);
    if (type === "ref") setCopiedRef(true);
    else setCopiedAccount(true);
    setTimeout(() => type === "ref" ? setCopiedRef(false) : setCopiedAccount(false), 2000);
    toast.info("Copied to clipboard!");
  };

  const platformCounts = useMemo(() => Object.fromEntries(platforms.map((p) => [p, dbServices.filter((s) => String(s?.platform || "").toLowerCase() === p.toLowerCase()).length])), [dbServices]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Social Marketplace"
        description="Browse Marketreum-powered products and services in the existing HopeSocial marketplace experience."
        actions={(
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1.5"><Zap className="h-3.5 w-3.5" />Marketreum catalog</Badge>
            <Badge variant="outline" className="gap-1.5"><ShieldCheck className="h-3.5 w-3.5" />Synced catalog</Badge>
          </div>
        )}
      />

      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
        <button onClick={() => setPlatform("all")} className={`flex shrink-0 items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition-all ${platform === "all" ? "bg-emerald-500 text-black shadow-md" : "border border-border/60 bg-card/80 text-muted-foreground hover:bg-muted"}`}>
          <Sparkles className="h-4 w-4" />All Platforms<span className="rounded-full bg-black/20 px-2 py-0.5 text-[10px]">{dbServices.length}</span>
        </button>
        {platforms.map((p) => {
          const Icon = platformIcons[p] || Sparkles;
          const style = platformStyles[p];
          return (
            <button key={p} onClick={() => setPlatform(p)} className={`flex shrink-0 items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold transition-all ${platform === p ? (style?.activePill || "bg-primary text-primary-foreground") : "border border-border/60 bg-card/80 text-muted-foreground hover:bg-muted"}`}>
              {createElement(Icon, { className: "h-3.5 w-3.5" })}<span>{p}</span><span className="rounded-full bg-muted/40 px-1.5 py-0.5 text-[10px] opacity-80">{platformCounts[p] || 0}</span>
            </button>
          );
        })}
      </div>

      <Card className="border-border/60 bg-card/80 backdrop-blur-sm shadow-sm">
        <CardContent className="flex flex-col gap-3 p-4 xl:flex-row xl:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input placeholder="Search products, services, categories or platforms…" value={q} onChange={(e) => setQ(e.target.value)} className="pl-9 bg-muted/40" />
          </div>
          <Select value={listingType} onValueChange={setListingType}>
            <SelectTrigger className="w-full xl:w-[170px] bg-muted/40"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="all">Products + Services</SelectItem><SelectItem value="product">Products only</SelectItem><SelectItem value="service">Services only</SelectItem></SelectContent>
          </Select>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger className="w-full xl:w-[210px] bg-muted/40"><SelectValue placeholder="All categories" /></SelectTrigger>
            <SelectContent><SelectItem value="all">All categories</SelectItem>{categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={sort} onValueChange={setSort}>
            <SelectTrigger className="w-full xl:w-[180px] bg-muted/40"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="popular">Most popular</SelectItem><SelectItem value="price-asc">Price: low to high</SelectItem><SelectItem value="price-desc">Price: high to low</SelectItem></SelectContent>
          </Select>
        </CardContent>
      </Card>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <Card key={i} className="h-64 animate-pulse border-border/60 bg-card/70" />)}
        </div>
      ) : filtered.length === 0 ? (
        <Card className="border-border/60 bg-card/60 py-16 text-center shadow-sm"><CardContent className="space-y-3"><ShoppingBag className="mx-auto h-10 w-10 text-muted-foreground/60" /><h3 className="text-base font-bold">No marketplace items found</h3><p className="mx-auto max-w-md text-xs text-muted-foreground">Marketreum products and services will appear here after the backend catalog sync is configured and run.</p></CardContent></Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {paged.map((item) => {
            const Icon = platformIcons[item.platform] || Sparkles;
            const style = platformStyles[item.platform] || { badgeBg: "bg-primary/15 text-primary border-primary/30", iconBg: "bg-primary text-primary-foreground" };
            const type = normalizeListingType(item);
            const price = getItemPrice(item);
            const isAvailable = item.is_active !== false && item.isActive !== false && item.in_stock !== false && item.inStock !== false;
            return (
              <Card key={item.id ?? `${item.platform}-${item.name}`} className={`group relative overflow-hidden border-border/60 bg-card transition-all duration-200 ${isAvailable ? "hover:-translate-y-1 hover:border-emerald-500/40 hover:shadow-lg" : "opacity-60 grayscale-[25%]"}`}>
                <CardContent className="flex h-full flex-col justify-between p-5">
                  <div>
                    <div className="mb-4 flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className={`grid h-11 w-11 shrink-0 place-items-center rounded-2xl ${style.iconBg} shadow-md`}>
                          {createElement(Icon, { className: "h-5 w-5" })}
                        </div>
                        <div className="min-w-0">
                          <div className="mb-1 flex items-center gap-2"><Badge variant="outline" className={style.badgeBg}>{item.platform || "Marketplace"}</Badge><Badge variant="outline" className="gap-1"><Package className="h-3 w-3" />{type === "product" ? "Product" : "Service"}</Badge></div>
                          <h3 className="truncate text-sm font-bold text-foreground" title={item.name}>{item.name}</h3>
                        </div>
                      </div>
                      <div className="shrink-0">{isAvailable ? <Badge className="bg-emerald-500/15 text-emerald-500 hover:bg-emerald-500/15">In stock</Badge> : <Badge variant="outline">Unavailable</Badge>}</div>
                    </div>

                    <p className="mb-4 min-h-10 text-xs leading-5 text-muted-foreground">{item.description || `Marketreum ${type} available through HopeSocial marketplace.`}</p>

                    <div className="mb-4 grid grid-cols-2 gap-2">
                      <div className="rounded-xl border border-border/60 bg-muted/30 p-3"><div className="text-[10px] uppercase tracking-wide text-muted-foreground">Category</div><div className="mt-1 truncate text-xs font-semibold" title={item.category}>{item.category || "General"}</div></div>
                      <div className="rounded-xl border border-border/60 bg-muted/30 p-3"><div className="text-[10px] uppercase tracking-wide text-muted-foreground">{type === "product" ? "Price" : "Rate / 1K"}</div><div className="mt-1 text-sm font-bold">₦{price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div></div>
                    </div>

                    {type === "service" && <div className="mb-4 flex items-center justify-between text-[11px] text-muted-foreground"><span>Min {item.min_order ?? item.min ?? 1}</span><span>Max {item.max_order ?? item.max ?? 100000}</span><span>{item.provider ? "Marketreum" : "Catalog item"}</span></div>}
                  </div>

                  <div className="flex gap-2">
                    <Button className="flex-1 gap-2" onClick={() => openOrderModal(item)} disabled={!isAvailable}><ShoppingBag className="h-4 w-4" />{type === "product" ? "Buy product" : "Order service"}</Button>
                    {item.external_url && <Button variant="outline" size="icon" asChild><a href={item.external_url} target="_blank" rel="noreferrer" aria-label={`Open ${item.name}`}><ExternalLink className="h-4 w-4" /></a></Button>}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {pages > 1 && <Pagination><PaginationContent>{page > 1 && <PaginationItem><PaginationPrevious href="#" onClick={(e) => { e.preventDefault(); setPage((p) => Math.max(1, p - 1)); }} /></PaginationItem>}{Array.from({ length: Math.min(pages, 7) }, (_, i) => i + 1).map((n) => <PaginationItem key={n}><PaginationLink href="#" isActive={page === n} onClick={(e) => { e.preventDefault(); setPage(n); }}>{n}</PaginationLink></PaginationItem>)}{page < pages && <PaginationItem><PaginationNext href="#" onClick={(e) => { e.preventDefault(); setPage((p) => Math.min(pages, p + 1)); }} /></PaginationItem>}</PaginationContent></Pagination>}

      <Dialog open={Boolean(selectedItem)} onOpenChange={(open) => !open && setSelectedItem(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader><DialogTitle>{normalizeListingType(selectedItem) === "product" ? "Buy product" : "Order service"}</DialogTitle><DialogDescription>{selectedItem?.name}</DialogDescription></DialogHeader>
          {selectedItem && (
            <div className="space-y-4">
              <div className="rounded-xl border border-border/60 bg-muted/30 p-4"><div className="flex items-center justify-between"><span className="text-sm text-muted-foreground">{normalizeListingType(selectedItem) === "product" ? "Unit price" : "Rate per 1,000"}</span><span className="text-lg font-bold">₦{getItemPrice(selectedItem).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div></div>
              {normalizeListingType(selectedItem) === "service" ? <>
                <div><label className="mb-2 block text-xs font-semibold">Target profile / post link</label><Input value={targetLink} onChange={(e) => setTargetLink(e.target.value)} placeholder="https://…" /></div>
                <div><label className="mb-2 block text-xs font-semibold">Quantity</label><div className="flex items-center gap-3"><Button type="button" variant="outline" size="icon" onClick={() => setOrderQuantity((v) => Math.max(Number(selectedItem.min_order ?? selectedItem.min ?? 1), Number(v) - 100))}><Minus className="h-4 w-4" /></Button><Input type="number" value={orderQuantity} onChange={(e) => setOrderQuantity(Math.max(Number(selectedItem.min_order ?? selectedItem.min ?? 1), Number(e.target.value) || 1))} className="text-center" /><Button type="button" variant="outline" size="icon" onClick={() => setOrderQuantity((v) => Math.min(Number(selectedItem.max_order ?? selectedItem.max ?? 100000), Number(v) + 100))}><Plus className="h-4 w-4" /></Button></div></div>
              </> : <div><label className="mb-2 block text-xs font-semibold">Quantity</label><Input type="number" min={1} value={orderQuantity} onChange={(e) => setOrderQuantity(Math.max(1, Number(e.target.value) || 1))} /></div>}
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4"><div className="flex items-center justify-between"><span className="text-sm text-muted-foreground">Estimated total</span><span className="text-xl font-bold">₦{(normalizeListingType(selectedItem) === "service" ? (orderQuantity / 1000) * getItemPrice(selectedItem) : orderQuantity * getItemPrice(selectedItem)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div></div>
            </div>
          )}
          <DialogFooter><Button variant="outline" onClick={() => setSelectedItem(null)}>Cancel</Button><Button onClick={handleProceedToPayment} className="gap-2">Continue to payment<ArrowRight className="h-4 w-4" /></Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isPaymentModalOpen} onOpenChange={setIsPaymentModalOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader><DialogTitle>Complete your order</DialogTitle><DialogDescription>Choose how you want to pay for {checkoutItem?.title}.</DialogDescription></DialogHeader>
          {checkoutItem && <div className="space-y-4">
            <div className="rounded-xl border border-border/60 bg-muted/20 p-4"><div className="mb-1 text-xs text-muted-foreground">Order total</div><div className="text-2xl font-bold">₦{checkoutItem.totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div><div className="mt-1 text-xs text-muted-foreground">Reference {checkoutItem.reference}</div></div>
            <Button className="w-full justify-between" onClick={() => handleCompletePayment("Wallet Balance")}><span className="flex items-center gap-2"><Wallet className="h-4 w-4" />Use wallet balance</span><ArrowRight className="h-4 w-4" /></Button>
            <div className="rounded-xl border border-border/60 bg-card p-4"><div className="mb-3 flex items-center gap-2 text-sm font-semibold"><Building2 className="h-4 w-4" />Direct bank transfer</div><div className="space-y-2 text-xs"><div className="flex items-center justify-between gap-3"><span className="text-muted-foreground">Bank</span><span className="font-semibold">{bankName}</span></div><div className="flex items-center justify-between gap-3"><span className="text-muted-foreground">Account name</span><span className="font-semibold">{accountName}</span></div><div className="flex items-center justify-between gap-3"><span className="text-muted-foreground">Account number</span><span className="font-semibold">{accountNumber}</span></div></div><div className="mt-3 flex gap-2"><Button variant="outline" size="sm" onClick={() => copyToClipboard(accountNumber, "account")} className="gap-2">{copiedAccount ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}Copy account</Button><Button variant="secondary" size="sm" onClick={() => copyToClipboard(checkoutItem.reference, "ref")} className="gap-2">{copiedRef ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}Copy reference</Button></div></div>
            <Button variant="outline" className="w-full justify-between" onClick={() => handleCompletePayment("Direct Bank Transfer")}><span className="flex items-center gap-2"><CreditCard className="h-4 w-4" />I have made the transfer</span><CheckCircle2 className="h-4 w-4" /></Button>
            {checkoutItem.externalUrl && <Button variant="ghost" className="w-full gap-2" asChild><a href={checkoutItem.externalUrl} target="_blank" rel="noreferrer">Open Marketreum listing<ExternalLink className="h-4 w-4" /></a></Button>}
          </div>}
        </DialogContent>
      </Dialog>
    </div>
  );
}

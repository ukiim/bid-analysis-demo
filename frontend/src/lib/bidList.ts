/**
 * 투찰리스트 — PDF 03 §9
 * localStorage 기반 누적 (계정별)
 */
export interface BidListItem {
  announcement_id: string;
  title: string;
  org: string;
  base_amount: number | null;
  predicted_rate: number;
  predicted_bid_amount: number | null;
  adjustment: number;
  added_at: string; // ISO
}

const KEY = "bid_list";

export function loadBidList(): BidListItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as BidListItem[]) : [];
  } catch {
    return [];
  }
}

export function saveBidList(items: BidListItem[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEY, JSON.stringify(items));
}

export function addToBidList(item: BidListItem) {
  const list = loadBidList();
  // 같은 공고는 덮어쓰기
  const filtered = list.filter((x) => x.announcement_id !== item.announcement_id);
  filtered.unshift(item);
  saveBidList(filtered);
  return filtered;
}

export function removeFromBidList(announcement_id: string) {
  const list = loadBidList();
  const filtered = list.filter((x) => x.announcement_id !== announcement_id);
  saveBidList(filtered);
  return filtered;
}

import { useMemo, useState } from "react";
import type { StockUniverseItem } from "../../lib/types";

interface StockUniversePickerProps {
  stocks: StockUniverseItem[];
  selectedSymbols: string[];
  onChange: (symbols: string[]) => void;
}

export function StockUniversePicker({ stocks, selectedSymbols, onChange }: StockUniversePickerProps) {
  const [query, setQuery] = useState("");

  const filteredStocks = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const selected = new Set(selectedSymbols);
    return stocks.filter((stock) => {
      if (selected.has(stock.symbol)) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      return [stock.symbol, stock.name, stock.sector, stock.industry].some((value) => value.toLowerCase().includes(normalizedQuery));
    });
  }, [query, selectedSymbols, stocks]);

  const selectedStocks = selectedSymbols.map((symbol) => stocks.find((stock) => stock.symbol === symbol)).filter(Boolean) as StockUniverseItem[];

  const addSymbol = (symbol: string) => {
    if (!selectedSymbols.includes(symbol)) {
      onChange([...selectedSymbols, symbol]);
    }
    setQuery("");
  };

  const removeSymbol = (symbol: string) => {
    onChange(selectedSymbols.filter((item) => item !== symbol));
  };

  return (
    <div className="stack-md">
      <label>
        Search the supported MVP universe
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search AAPL, healthcare, software..." />
      </label>
      <div className="badge-cloud">
        {selectedStocks.map((stock) => (
          <button key={stock.symbol} type="button" className="symbol-badge" onClick={() => removeSymbol(stock.symbol)}>
            <strong>{stock.symbol}</strong>
            <span>{stock.name}</span>
          </button>
        ))}
      </div>
      <div className="stock-search-results">
        {filteredStocks.length === 0 ? (
          <div className="empty-inline-state">No matching stocks in the MVP universe.</div>
        ) : (
          filteredStocks.map((stock) => (
            <button key={stock.symbol} type="button" className="stock-result-card" onClick={() => addSymbol(stock.symbol)}>
              <div>
                <strong>{stock.symbol}</strong>
                <p>{stock.name}</p>
              </div>
              <div className="stock-meta">
                <span>{stock.sector}</span>
                <small>{stock.industry}</small>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

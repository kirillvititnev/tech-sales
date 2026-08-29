"use client";

import { FormEvent, useEffect, useId, useState } from "react";

import { API_URL, apiErrorMessage } from "@/lib/api";
import { adminFetch } from "@/lib/adminFetch";

type MatchKind = "brand" | "category" | "kind";

type RuleDraft = {
  match: MatchKind;
  value: string;
  percent: string;
  error: string | null;
};

const MAX_RULES = 50;
const MATCH_OPTIONS: { value: MatchKind; label: string }[] = [
  { value: "brand", label: "Бренд" },
  { value: "category", label: "Категория" },
  { value: "kind", label: "Тип" },
];

function emptyRule(): RuleDraft {
  return { match: "brand", value: "", percent: "0", error: null };
}

function parsePercent(raw: string): number | null {
  const n = Number(raw.replace(",", ".").trim());
  if (!Number.isFinite(n)) return null;
  return n;
}

function isMatch(value: string): value is MatchKind {
  return value === "brand" || value === "category" || value === "kind";
}

export default function AdminSettingsPage() {
  const formId = useId();
  const [markup, setMarkup] = useState("0");
  const [roundTo, setRoundTo] = useState("100");
  const [l1, setL1] = useState("5");
  const [l2, setL2] = useState("2");
  const [l3, setL3] = useState("1");
  const [rules, setRules] = useState<RuleDraft[]>([]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function applySettings(data: {
    default_markup_percent: string | number;
    price_round_to: string | number;
    referral_percent_l1?: string | number;
    referral_percent_l2?: string | number;
    referral_percent_l3?: string | number;
    markup_rules?: { match?: string; value?: string; percent?: string | number }[];
  }) {
    setMarkup(String(data.default_markup_percent));
    setRoundTo(String(data.price_round_to));
    setL1(String(data.referral_percent_l1 ?? "5"));
    setL2(String(data.referral_percent_l2 ?? "2"));
    setL3(String(data.referral_percent_l3 ?? "1"));
    setRules(
      (data.markup_rules ?? []).map((rule) => ({
        match: isMatch(rule.match ?? "") ? rule.match : "brand",
        value: rule.value ?? "",
        percent: String(rule.percent ?? "0"),
        error: null,
      })),
    );
  }

  useEffect(() => {
    (async () => {
      try {
        const res = await adminFetch(`${API_URL}/api/v1/admin/settings`);
        if (!res.ok) throw new Error("fail");
        applySettings(await res.json());
      } catch {
        setError("Не удалось загрузить настройки");
      }
    })();
  }, []);

  function setRule(index: number, patch: Partial<RuleDraft>) {
    setRules((prev) => prev.map((rule, i) => (i === index ? { ...rule, ...patch } : rule)));
  }

  function validate(): boolean {
    const next: Record<string, string> = {};
    const defaultPct = parsePercent(markup);
    if (defaultPct === null || defaultPct < 0 || defaultPct > 100) {
      next.markup = "Укажите наценку от 0 до 100";
    }
    const round = Number(roundTo);
    if (!Number.isFinite(round) || round < 1 || round > 10000) {
      next.roundTo = "Округление — целое число от 1 до 10 000";
    }
    const refs: [string, string][] = [
      ["l1", l1],
      ["l2", l2],
      ["l3", l3],
    ];
    for (const [key, value] of refs) {
      const pct = parsePercent(value);
      if (pct === null || pct < 0 || pct > 50) {
        next[key] = "Рефералка — от 0 до 50";
      }
    }
    const nextRules = rules.map((rule) => {
      if (!rule.value.trim()) {
        return { ...rule, error: "Нужно значение" };
      }
      const pct = parsePercent(rule.percent);
      if (pct === null || pct < 0 || pct > 100) {
        return { ...rule, error: "Наценка правила — от 0 до 100" };
      }
      return { ...rule, error: null };
    });
    setRules(nextRules);
    setFieldErrors(next);
    return Object.keys(next).length === 0 && nextRules.every((rule) => !rule.error);
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    setError(null);
    if (!validate()) return;
    setBusy(true);
    try {
      const res = await adminFetch(`${API_URL}/api/v1/admin/settings`, {
        method: "PATCH",
        body: JSON.stringify({
          default_markup_percent: Number(markup.replace(",", ".")),
          price_round_to: Number(roundTo),
          referral_percent_l1: Number(l1.replace(",", ".")),
          referral_percent_l2: Number(l2.replace(",", ".")),
          referral_percent_l3: Number(l3.replace(",", ".")),
          markup_rules: rules.map((rule) => ({
            match: rule.match,
            value: rule.value.trim(),
            percent: Number(rule.percent.replace(",", ".")),
          })),
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(apiErrorMessage(data, "Ошибка сохранения"));
        return;
      }
      applySettings(await res.json());
      setFieldErrors({});
      setMessage("Сохранено. Наценка подхватит следующие синки; рефералка действует на новые оплаты.");
    } catch {
      setError("Сеть недоступна");
    } finally {
      setBusy(false);
    }
  }

  function addRule() {
    if (rules.length >= MAX_RULES) return;
    setRules((prev) => [...prev, emptyRule()]);
  }

  function removeRule(index: number) {
    const ok = window.confirm("Удалить это правило наценки?");
    if (!ok) return;
    setRules((prev) => prev.filter((_, i) => i !== index));
  }

  return (
    <main className="section">
      <h2>Настройки</h2>
      <p className="lead">
        Базовая наценка витрины, округление до 100 ₽ и правила по бренду, категории или типу. Первое
        совпадение побеждает. Уведомления о заказах уходят в Telegram, если заданы токен бота и чат
        администратора.
      </p>
      <form className="checkout-form settings-form" onSubmit={onSave}>
        <div className="account-groups">
          <section className="account-group">
            <h3>Витрина</h3>
            <label htmlFor={`${formId}-markup`}>
              Наценка, %
              <input
                id={`${formId}-markup`}
                value={markup}
                onChange={(e) => {
                  setMarkup(e.target.value);
                  setFieldErrors((prev) => ({ ...prev, markup: "" }));
                }}
                type="number"
                min={0}
                max={100}
                step="0.1"
                aria-invalid={fieldErrors.markup ? true : undefined}
                aria-describedby={fieldErrors.markup ? `${formId}-markup-error` : undefined}
              />
            </label>
            {fieldErrors.markup ? (
              <p className="form-error" id={`${formId}-markup-error`} role="alert">
                {fieldErrors.markup}
              </p>
            ) : null}
            <label htmlFor={`${formId}-round`}>
              Округление до, ₽
              <input
                id={`${formId}-round`}
                value={roundTo}
                onChange={(e) => {
                  setRoundTo(e.target.value);
                  setFieldErrors((prev) => ({ ...prev, roundTo: "" }));
                }}
                type="number"
                min={1}
                max={10000}
                aria-invalid={fieldErrors.roundTo ? true : undefined}
                aria-describedby={fieldErrors.roundTo ? `${formId}-round-error` : undefined}
              />
            </label>
            {fieldErrors.roundTo ? (
              <p className="form-error" id={`${formId}-round-error`} role="alert">
                {fieldErrors.roundTo}
              </p>
            ) : null}
          </section>

          <section className="account-group">
            <h3>Рефералка</h3>
            {(
              [
                ["l1", "Рефералка L1, %", l1, setL1],
                ["l2", "Рефералка L2, %", l2, setL2],
                ["l3", "Рефералка L3, %", l3, setL3],
              ] as const
            ).map(([key, label, value, setter]) => (
              <div key={key}>
                <label htmlFor={`${formId}-${key}`}>
                  {label}
                  <input
                    id={`${formId}-${key}`}
                    value={value}
                    onChange={(e) => {
                      setter(e.target.value);
                      setFieldErrors((prev) => ({ ...prev, [key]: "" }));
                    }}
                    type="number"
                    min={0}
                    max={50}
                    step="0.1"
                    aria-invalid={fieldErrors[key] ? true : undefined}
                    aria-describedby={fieldErrors[key] ? `${formId}-${key}-error` : undefined}
                  />
                </label>
                {fieldErrors[key] ? (
                  <p className="form-error" id={`${formId}-${key}-error`} role="alert">
                    {fieldErrors[key]}
                  </p>
                ) : null}
              </div>
            ))}
          </section>

          <section className="account-group">
            <h3>Правила наценки</h3>
            <p className="account-meta">
              Категория — как на витрине, например «Смартфоны ASIS». Тип — iphone, samsung, dyson.
            </p>
            {rules.length === 0 ? (
              <p className="account-meta">Правил пока нет — действует базовая наценка.</p>
            ) : (
              <ul className="account-list settings-rules">
                {rules.map((rule, index) => {
                  const errorId = `${formId}-rule-${index}-error`;
                  return (
                    <li key={`${formId}-rule-${index}`} className="settings-rule">
                      <div className="settings-rule-fields">
                        <label htmlFor={`${formId}-rule-${index}-match`}>
                          Совпадение
                          <select
                            id={`${formId}-rule-${index}-match`}
                            value={rule.match}
                            onChange={(e) =>
                              setRule(index, {
                                match: isMatch(e.target.value) ? e.target.value : "brand",
                                error: null,
                              })
                            }
                          >
                            {MATCH_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label htmlFor={`${formId}-rule-${index}-value`}>
                          Значение
                          <input
                            id={`${formId}-rule-${index}-value`}
                            value={rule.value}
                            onChange={(e) => setRule(index, { value: e.target.value, error: null })}
                            maxLength={128}
                            aria-invalid={rule.error ? true : undefined}
                            aria-describedby={rule.error ? errorId : undefined}
                          />
                        </label>
                        <label htmlFor={`${formId}-rule-${index}-percent`}>
                          Наценка, %
                          <input
                            id={`${formId}-rule-${index}-percent`}
                            value={rule.percent}
                            onChange={(e) => setRule(index, { percent: e.target.value, error: null })}
                            type="number"
                            min={0}
                            max={100}
                            step="0.1"
                            aria-invalid={rule.error ? true : undefined}
                            aria-describedby={rule.error ? errorId : undefined}
                          />
                        </label>
                      </div>
                      {rule.error ? (
                        <p className="form-error" id={errorId} role="alert">
                          {rule.error}
                        </p>
                      ) : null}
                      <button
                        type="button"
                        className="btn btn-ghost admin-btn"
                        onClick={() => removeRule(index)}
                      >
                        Удалить
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
            <button
              type="button"
              className="btn btn-ghost admin-btn"
              onClick={addRule}
              disabled={rules.length >= MAX_RULES}
            >
              Добавить правило
            </button>
          </section>
        </div>

        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}
        {message ? (
          <p className="lead" role="status">
            {message}
          </p>
        ) : null}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          Сохранить
        </button>
      </form>
    </main>
  );
}

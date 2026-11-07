// User-facing labels shared by every page. French only for now; an Arabic
// dictionary can be added with the same keys (NFR-11: Arabic-ready).
import type { SheetStatus, Status } from './api'

export const STATUS: Record<Status, { label: string; tone: string }> = {
  new: { label: 'Nouveau', tone: 'info' },
  confirmed: { label: 'Confirmé', tone: 'warn' },
  sheet_sent: { label: 'Fiche transmise', tone: 'serious' },
  fixed: { label: 'Réparé', tone: 'good' },
  rejected: { label: 'Rejeté', tone: 'muted' },
  reopened: { label: 'Rouvert', tone: 'critical' },
}

export const SHEET: Record<SheetStatus, { label: string; tone: string }> = {
  queued: { label: 'Fiche en cours', tone: 'info' },
  generated: { label: 'Fiche à valider', tone: 'warn' },
  approved: { label: 'Fiche approuvée', tone: 'good' },
  failed: { label: 'Fiche en échec', tone: 'critical' },
}

export const PRIORITY_PARTS: Record<string, string> = {
  severity: 'Sévérité',
  road: 'Type de route',
  confirmations: 'Citoyens',
  age: 'Ancienneté',
  overdue: 'Échéance dépassée',
  reopened: 'Rouvert',
  rain: 'Pluie prévue',
}

export const ROAD_CLASS: Record<string, string> = {
  national: 'Route nationale',
  regional: 'Route régionale',
  local: 'Route locale',
  urbain_principal: 'Axe urbain principal',
  urbain_secondaire: 'Rue urbaine',
  rural: 'Route rurale',
  piste: 'Piste',
  autoroute: 'Autoroute',
}

export const SOURCE: Record<string, string> = { manual: 'Application', driving_mode: 'Mode conduite', web: 'Web' }

export const EVENT: Record<string, string> = {
  created: 'Premier signalement',
  report_added: 'Nouveau signalement',
  status: 'Changement de statut',
  enriched: 'Route et bureau identifiés (OpenStreetMap)',
  sheet_generated: 'Fiche rédigée',
  sheet_edited: 'Fiche modifiée',
  sheet_approved: 'Fiche approuvée',
  sheet_retry: 'Nouvelle tentative de fiche',
  escalated: 'Escaladé au bureau supérieur',
  fix_check_passed: 'Photo de réparation vérifiée par l’IA',
  fix_check_failed: 'L’IA voit encore un nid-de-poule sur la photo de réparation',
  confirmation_seen: '« Je le vois aussi »',
  confirmation_not_fixed: '« Toujours là »',
  confirmation_fixed_ok: '« Bien réparé »',
  confirmation_not_pothole: '« Pas un nid-de-poule »',
  feedback_not_pothole: 'Étiqueté « pas un nid-de-poule »',
  feedback_confirmed_pothole: 'Étiqueté « nid-de-poule »',
}

export const priorityExplanation = (parts: Record<string, number>) =>
  Object.entries(parts)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => `${PRIORITY_PARTS[k] ?? k} +${Math.round(v * 10) / 10}`)
    .join(' · ')

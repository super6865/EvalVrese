/**
 * Date utility functions for handling UTC timestamps from backend
 * 
 * Backend stores timestamps in UTC using datetime.utcnow() and serializes
 * them as ISO 8601 strings without timezone indicator (e.g., "2025-12-03T08:31:06.000000").
 * This utility ensures proper conversion from UTC to local timezone for display.
 */
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

// Extend dayjs with UTC and timezone plugins
dayjs.extend(utc)
dayjs.extend(timezone)

/**
 * Format a UTC timestamp string to local timezone
 * 
 * @param timestamp - ISO 8601 timestamp string from backend (UTC, may or may not have 'Z' suffix)
 * @param format - Format string (default: 'YYYY-MM-DD HH:mm:ss')
 * @returns Formatted date string in local timezone, or '-' if timestamp is null/undefined/empty
 */
export function formatTimestamp(
  timestamp: string | null | undefined,
  format: string = 'YYYY-MM-DD HH:mm:ss'
): string {
  if (!timestamp) {
    return '-'
  }

  // Parse the timestamp as UTC and convert to local timezone
  // If the string doesn't have 'Z' suffix, we assume it's UTC
  const utcTime = timestamp.endsWith('Z') 
    ? dayjs.utc(timestamp)
    : dayjs.utc(timestamp + 'Z')
  
  return utcTime.local().format(format)
}

/**
 * Format a UTC timestamp string with milliseconds
 * 
 * @param timestamp - ISO 8601 timestamp string from backend (UTC)
 * @returns Formatted date string with milliseconds in local timezone
 */
export function formatTimestampWithMs(
  timestamp: string | null | undefined
): string {
  return formatTimestamp(timestamp, 'YYYY-MM-DD HH:mm:ss.SSS')
}


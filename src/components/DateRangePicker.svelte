<script lang="ts">
	import { Calendar, Check, CircleAlert } from 'lucide';
	import {
		applyDayClick,
		formatMDY,
		outputState,
		parseDateKey,
		toDateKey,
		type DateKey,
	} from '../lib/dateRangePickerLogic';
	import { captureEvent, SOURCE_PAGE } from '../lib/analytics';
	import LucideIcon from './LucideIcon.svelte';

	let {
		id = 'date-range-picker',
		labelledBy,
	}: {
		id?: string;
		labelledBy?: string;
	} = $props();

	let start = $state<DateKey | null>(null);
	let end = $state<DateKey | null>(null);
	let expanded = $state(false);
	/** First month (0–11) of the left calendar when expanded */
	let viewYear = $state(new Date().getFullYear());
	let viewMonth0 = $state(new Date().getMonth());

	/** Skip analytics on the first range dispatch (initial sync). */
	let dateRangeAnalyticsReady = false;

	const state = $derived(outputState(start, end));

	function dispatchRange() {
		const detail =
			state === 'valid' && start && end
				? { state: 'valid' as const, start: start!, end: end! }
				: { state: state, start: null, end: null };
		document.dispatchEvent(
			new CustomEvent('runningcalendar:daterange', { detail, bubbles: true }),
		);
		if (
			dateRangeAnalyticsReady &&
			detail.state === 'valid' &&
			detail.start &&
			detail.end
		) {
			captureEvent('date_range_selected', {
				date_range_start: detail.start,
				date_range_end: detail.end,
				source_page: SOURCE_PAGE,
			});
		}
		dateRangeAnalyticsReady = true;
	}

	$effect(() => {
		dispatchRange();
	});

	function setViewFromKey(key: DateKey | null) {
		const p = key ? parseDateKey(key) : null;
		if (p) {
			viewYear = p.y;
			viewMonth0 = p.m0;
		}
	}

	function close() {
		expanded = false;
	}

	/**
	 * Opening uses mousedown so the following `click` does not immediately toggle closed.
	 * (Same issue as popover + toggle on one control.)
	 */
	let skipNextTriggerClick = $state(false);

	function onTriggerMouseDown() {
		if (!expanded) {
			skipNextTriggerClick = true;
			expanded = true;
			if (start) setViewFromKey(start);
		}
	}

	function onTriggerClick() {
		if (skipNextTriggerClick) {
			skipNextTriggerClick = false;
			return;
		}
		expanded = !expanded;
		if (expanded && start) setViewFromKey(start);
	}

	function onRootFocusOut(e: FocusEvent) {
		const root = e.currentTarget as HTMLElement;
		const rt = e.relatedTarget as Node | null;
		if (rt && root.contains(rt)) return;
		/* relatedTarget is often null when tabbing or moving focus programmatically; defer so activeElement has settled */
		setTimeout(() => {
			if (!root.contains(document.activeElement)) close();
		}, 0);
	}

	function onDayClick(key: DateKey) {
		const next = applyDayClick(start, end, key);
		start = next.start;
		end = next.end;
	}

	function clearRange() {
		start = null;
		end = null;
	}

	function applyAndClose() {
		close();
		const trigger = document.getElementById(`${id}-trigger`);
		trigger?.focus();
	}

	const collapsedLabel = $derived.by(() => {
		if (!start && !end) return 'Selecione as datas';
		if (start && !end) return `${formatMDY(start)} — Data final`;
		if (start && end) return `${formatMDY(start)} — ${formatMDY(end)}`;
		return 'Selecione as datas';
	});

	const summaryText = $derived.by(() => {
		if (start && end) return `${formatMDY(start)} — ${formatMDY(end)}`;
		if (start) return `${formatMDY(start)} — Data final`;
		return 'Nenhum intervalo selecionado';
	});

	function monthLabel(y: number, m0: number): string {
		return new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' }).format(
			new Date(y, m0, 1),
		);
	}

	function daysMatrix(y: number, m0: number): { key: DateKey; inMonth: boolean }[] {
		const first = new Date(y, m0, 1);
		const startPad = first.getDay();
		const daysInMonth = new Date(y, m0 + 1, 0).getDate();
		const cells: { key: DateKey; inMonth: boolean }[] = [];
		const prevMonthLast = new Date(y, m0, 0).getDate();
		for (let i = 0; i < startPad; i++) {
			const d = prevMonthLast - startPad + i + 1;
			const pm = m0 === 0 ? 11 : m0 - 1;
			const py = m0 === 0 ? y - 1 : y;
			cells.push({ key: toDateKey(py, pm, d), inMonth: false });
		}
		for (let d = 1; d <= daysInMonth; d++) {
			cells.push({ key: toDateKey(y, m0, d), inMonth: true });
		}
		let ty = y;
		let tm0 = m0 + 1;
		if (tm0 > 11) {
			tm0 = 0;
			ty += 1;
		}
		let td = 1;
		while (cells.length < 42) {
			const dim = new Date(ty, tm0 + 1, 0).getDate();
			if (td > dim) {
				td = 1;
				tm0 += 1;
				if (tm0 > 11) {
					tm0 = 0;
					ty += 1;
				}
			}
			cells.push({
				key: toDateKey(ty, tm0, td),
				inMonth: tm0 === m0 && ty === y,
			});
			td += 1;
		}
		return cells;
	}

	const monthLeft = $derived({ y: viewYear, m0: viewMonth0 });
	const monthRight = $derived.by(() => {
		let y = viewYear;
		let m0 = viewMonth0 + 1;
		if (m0 > 11) {
			m0 = 0;
			y += 1;
		}
		return { y, m0 };
	});

	function shiftView(delta: number) {
		let m = viewMonth0 + delta;
		let y = viewYear;
		while (m < 0) {
			m += 12;
			y -= 1;
		}
		while (m > 11) {
			m -= 12;
			y += 1;
		}
		viewMonth0 = m;
		viewYear = y;
	}

	function dayRole(key: DateKey): 'start' | 'end' | 'between' | 'none' {
		if (!start) return 'none';
		if (!end) {
			return key === start ? 'start' : 'none';
		}
		if (start === end) {
			return key === start ? 'start' : 'none';
		}
		if (key === start) return 'start';
		if (key === end) return 'end';
		if (key > start && key < end!) return 'between';
		return 'none';
	}

	const weekdays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
</script>

<div
	class="drp"
	class:drp--expanded={expanded}
	class:drp--inactive={state === 'inactive'}
	class:drp--invalid={state === 'invalid'}
	class:drp--valid={state === 'valid'}
	data-testid="date-range-picker"
	data-state={state}
	onfocusout={onRootFocusOut}
>
	<div class="drp__field-wrap">
		<button
			type="button"
			class="drp__trigger"
			id="{id}-trigger"
			aria-expanded={expanded}
			aria-haspopup="dialog"
			aria-controls="{id}-popover"
			aria-labelledby={labelledBy}
			data-testid="date-range-trigger"
			onmousedown={onTriggerMouseDown}
			onclick={onTriggerClick}
		>
			<span class="drp__trigger-icon" aria-hidden="true">
				<LucideIcon icon={Calendar} size={18} aria-hidden={true} />
			</span>
			<span class="drp__trigger-text">{collapsedLabel}</span>
			<span class="drp__trigger-trail">
				{#if state === 'valid'}
					<span class="drp__icon-ok" aria-hidden="true" data-testid="drp-valid-icon">
						<LucideIcon icon={Check} size={18} strokeWidth={2.2} aria-hidden={true} />
					</span>
				{:else if state === 'invalid'}
					<span class="drp__icon-warn" aria-hidden="true" data-testid="drp-invalid-icon">
						<LucideIcon icon={CircleAlert} size={18} aria-hidden={true} />
					</span>
				{/if}
			</span>
		</button>

		{#if expanded}
			<div
				class="drp__popover"
				id="{id}-popover"
				role="dialog"
				aria-label="Escolher intervalo de datas"
				data-testid="date-range-popover"
			>
				<div class="drp__popover-inner">
					<div class="drp__months">
						{#each [monthLeft, monthRight] as mm, idx (idx)}
							<div class="drp__month">
								<div class="drp__month-head">
									{#if idx === 0}
										<button
											type="button"
											class="drp__nav"
											aria-label="Mês anterior"
											data-testid="drp-prev-month"
											onclick={() => shiftView(-1)}
										>
											‹
										</button>
									{:else}
										<span class="drp__nav-spacer"></span>
									{/if}
									<span class="drp__month-title">{monthLabel(mm.y, mm.m0)}</span>
									{#if idx === 1}
										<div class="drp__nav-group">
											<button
												type="button"
												class="drp__nav"
												aria-label="Próximo mês"
												data-testid="drp-next-month"
												onclick={() => shiftView(1)}
											>
												›
											</button>
											<button
												type="button"
												class="drp__nav"
												aria-label="Avançar um mês"
												data-testid="drp-next-month-2"
												onclick={() => shiftView(1)}
											>
												›
											</button>
										</div>
									{:else}
										<span class="drp__nav-spacer"></span>
									{/if}
								</div>
								<div class="drp__weekdays">
									{#each weekdays as w}
										<span>{w}</span>
									{/each}
								</div>
								<div class="drp__grid">
									{#each daysMatrix(mm.y, mm.m0) as cell (cell.key)}
										{@const role = dayRole(cell.key)}
										<button
											type="button"
											class="drp__day"
											class:drp__day--muted={!cell.inMonth}
											class:drp__day--start={role === 'start'}
											class:drp__day--end={role === 'end'}
											class:drp__day--between={role === 'between'}
											data-day={cell.key}
											data-testid="drp-day"
											onclick={() => onDayClick(cell.key)}
										>
											{parseDateKey(cell.key)?.d ?? ''}
										</button>
									{/each}
								</div>
							</div>
						{/each}
					</div>

					<div class="drp__footer">
						<button
							type="button"
							class="drp__link"
							data-testid="drp-clear-footer"
							onclick={clearRange}
						>
							Limpar
						</button>
						<div class="drp__footer-right">
							{#if state === 'valid'}
								<span class="drp__summary drp__summary--ok" data-testid="drp-summary">
									<span class="drp__icon-ok" aria-hidden="true">
										<LucideIcon icon={Check} size={16} strokeWidth={2.2} aria-hidden={true} />
									</span>
									{summaryText}
								</span>
							{:else}
								<span class="drp__summary" data-testid="drp-summary">{summaryText}</span>
							{/if}
							<button type="button" class="drp__btn drp__btn--ghost" onclick={clearRange}>Limpar</button>
							<button type="button" class="drp__btn drp__btn--primary" data-testid="drp-apply" onclick={applyAndClose}>
								Aplicar
							</button>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.drp {
		position: relative;
		min-width: 0;
		width: 100%;
		/* Popover extends below; avoid clipping from ancestor overflow */
		overflow: visible;
		z-index: 1;
	}

	.drp--expanded {
		z-index: 10;
	}

	.drp__field-wrap {
		position: relative;
		overflow: visible;
	}

	.drp__trigger {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		width: 100%;
		margin: 0;
		padding: var(--space-sm) var(--space-md);
		font-size: var(--text-body);
		font-weight: var(--font-weight-regular);
		line-height: 1.4;
		color: var(--color-text-primary);
		background: var(--color-background);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
		text-align: left;
	}

	.drp--valid .drp__trigger {
		border-color: var(--color-primary);
		box-shadow: 0 0 0 1px var(--color-primary);
	}

	.drp--invalid .drp__trigger {
		border-color: var(--color-danger);
		box-shadow: 0 0 0 1px var(--color-danger);
	}

	.drp__trigger:focus-visible {
		outline: none;
		border-color: var(--color-secondary);
		box-shadow: 0 0 0 3px rgb(244 162 97 / 35%);
	}

	.drp--valid .drp__trigger:focus-visible {
		border-color: var(--color-primary);
		box-shadow: 0 0 0 3px rgb(11 110 79 / 22%);
	}

	.drp--invalid .drp__trigger:focus-visible {
		border-color: var(--color-danger);
		box-shadow: 0 0 0 3px rgb(231 111 81 / 28%);
	}

	.drp__trigger-icon {
		flex-shrink: 0;
		color: var(--color-primary);
		display: flex;
	}

	.drp__trigger-text {
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.drp__trigger-trail {
		flex-shrink: 0;
		display: flex;
		align-items: center;
	}

	.drp__icon-ok {
		color: var(--color-primary);
		display: flex;
	}

	.drp__icon-warn {
		color: var(--color-danger);
		display: flex;
	}

	.drp__clear {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.75rem;
		height: 1.75rem;
		margin: 0;
		padding: 0;
		font-size: 1.25rem;
		line-height: 1;
		color: var(--color-text-secondary);
		background: transparent;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
	}

	.drp__clear:hover {
		color: var(--color-text-primary);
		background: var(--color-surface);
	}

	.drp__popover {
		position: absolute;
		z-index: 100;
		left: 0;
		right: 0;
		margin-top: var(--space-xs);
		padding: var(--space-md);
		background: var(--color-background);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-lg);
	}

	@media (min-width: 640px) {
		.drp__popover {
			min-width: min(100%, 38rem);
			right: auto;
		}
	}

	.drp__months {
		display: grid;
		gap: var(--space-lg);
	}

	@media (min-width: 480px) {
		.drp__months {
			grid-template-columns: 1fr 1fr;
		}
	}

	.drp__month-head {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: var(--space-xs);
		margin-bottom: var(--space-sm);
	}

	.drp__month-title {
		font-size: var(--text-meta);
		font-weight: var(--font-weight-semibold);
		text-align: center;
	}

	.drp__nav {
		width: 2rem;
		height: 2rem;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		margin: 0;
		padding: 0;
		font-size: 1.25rem;
		line-height: 1;
		color: var(--color-text-primary);
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		cursor: pointer;
	}

	.drp__nav:hover {
		border-color: var(--color-primary);
	}

	.drp__nav-spacer {
		width: 2rem;
		height: 2rem;
	}

	.drp__nav-group {
		display: inline-flex;
		gap: var(--space-xs);
	}

	.drp__weekdays {
		display: grid;
		grid-template-columns: repeat(7, 1fr);
		gap: 0;
		margin-bottom: var(--space-xs);
		font-size: var(--text-caption);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-secondary);
		text-align: center;
	}

	.drp__grid {
		display: grid;
		grid-template-columns: repeat(7, 1fr);
		gap: 0;
	}

	.drp__day {
		position: relative;
		aspect-ratio: 1;
		max-height: 2.25rem;
		margin: 0;
		padding: 0;
		font-size: var(--text-caption);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-primary);
		background: transparent;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
	}

	.drp__day--muted {
		color: var(--color-text-secondary);
		opacity: 0.55;
	}

	.drp__day:hover {
		outline: 2px solid var(--color-secondary);
		outline-offset: 1px;
		z-index: 1;
	}

	.drp__day:focus-visible {
		outline: 2px solid var(--color-secondary);
		outline-offset: 1px;
		z-index: 1;
	}

	.drp__day--between {
		background: rgb(11 110 79 / 14%);
		border-radius: 0;
	}

	.drp__day--start,
	.drp__day--end {
		background: var(--color-primary);
		color: var(--color-background);
		border-radius: 999px;
		outline: none;
	}

	.drp__day--start.drp__day--between,
	.drp__day--end.drp__day--between {
		border-radius: 999px;
	}

	.drp__footer {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-md);
		margin-top: var(--space-lg);
		padding-top: var(--space-md);
		border-top: 1px solid var(--color-border);
	}

	.drp__link {
		margin: 0;
		padding: 0;
		font: inherit;
		font-size: var(--text-meta);
		font-weight: var(--font-weight-semibold);
		color: var(--color-primary);
		background: none;
		border: none;
		cursor: pointer;
		text-decoration: underline;
		text-underline-offset: 2px;
	}

	.drp__footer-right {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: flex-end;
		gap: var(--space-sm);
		flex: 1;
		min-width: 0;
	}

	.drp__summary {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		font-size: var(--text-caption);
		color: var(--color-text-secondary);
	}

	.drp__summary--ok {
		color: var(--color-text-primary);
	}

	.drp__btn {
		margin: 0;
		padding: var(--space-xs) var(--space-md);
		font-size: var(--text-caption);
		font-weight: var(--font-weight-semibold);
		border-radius: var(--radius-sm);
		cursor: pointer;
	}

	.drp__btn--ghost {
		color: var(--color-primary);
		background: var(--color-background);
		border: 1px solid var(--color-primary);
	}

	.drp__btn--primary {
		color: var(--color-background);
		background: var(--color-primary);
		border: 1px solid var(--color-primary);
	}

	.drp__btn--primary:hover {
		background: var(--color-primary-hover);
		border-color: var(--color-primary-hover);
	}
</style>

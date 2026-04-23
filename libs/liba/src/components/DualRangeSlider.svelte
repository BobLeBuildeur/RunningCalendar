<script lang="ts">
	type FormatFn = (value: number) => string;

	let {
		min,
		max,
		start = $bindable(),
		end = $bindable(),
		step = 0.1,
		formatValue = ((v: number) => String(v)) as FormatFn,
		formatMinLabel,
		formatMaxLabel,
		formatRange,
		labelledBy,
		id: sliderId = `dual-range-${Math.random().toString(36).slice(2, 9)}`,
	}: {
		min: number;
		max: number;
		start: number;
		end: number;
		step?: number;
		formatValue?: FormatFn;
		/** Override left track label (defaults to `formatValue(min)`). */
		formatMinLabel?: FormatFn;
		/** Override right track label (defaults to `formatValue(max)`). */
		formatMaxLabel?: FormatFn;
		/** Center summary; default: `start — end` with `formatValue`. */
		formatRange?: (start: number, end: number) => string;
		/** Prefix for input ids (accessibility). */
		id?: string;
		/** External element id for the field label (e.g. "Distance"); pairs with value text for screen readers. */
		labelledBy?: string;
	} = $props();

	const ariaLabelledBy = $derived(
		labelledBy ? `${labelledBy} ${sliderId}-value` : `${sliderId}-value`,
	);

	const minL = $derived(formatMinLabel?.(min) ?? formatValue(min));
	const maxL = $derived(formatMaxLabel?.(max) ?? formatValue(max));
	const rangeText = $derived(
		formatRange?.(start, end) ?? `${formatValue(start)} — ${formatValue(end)}`,
	);

	/** Upper bound for start thumb and lower bound for end thumb (native range cannot cross). */
	const startInputMax = $derived(Math.min(max, end));
	const endInputMin = $derived(Math.max(min, start));

	/** Percent 0–100 of value within [min, max] */
	function pct(value: number): number {
		if (max <= min) return 0;
		return ((value - min) / (max - min)) * 100;
	}

	/**
	 * Each input only spans the sub-range it controls; width/offset match the global track so thumb
	 * position stays correct while `min`/`max` on the element enforce the collision stop.
	 */
	const startSegWidthPct = $derived(max <= min ? 100 : ((end - min) / (max - min)) * 100);
	const endSegLeftPct = $derived(pct(start));
	const endSegWidthPct = $derived(max <= min ? 100 : ((max - start) / (max - min)) * 100);

	function clampStart(v: number): number {
		const lo = min;
		const hi = Math.min(max, end);
		return Math.min(Math.max(v, lo), hi);
	}

	function clampEnd(v: number): number {
		const lo = Math.max(min, start);
		const hi = max;
		return Math.min(Math.max(v, lo), hi);
	}

	function onStartInput(e: Event) {
		const el = e.currentTarget;
		if (!(el instanceof HTMLInputElement)) return;
		const v = Number(el.value);
		if (!Number.isFinite(v)) return;
		start = clampStart(v);
	}

	function onEndInput(e: Event) {
		const el = e.currentTarget;
		if (!(el instanceof HTMLInputElement)) return;
		const v = Number(el.value);
		if (!Number.isFinite(v)) return;
		end = clampEnd(v);
	}

	const fillLeft = $derived(pct(start));
	const fillWidth = $derived(Math.max(0, pct(end) - pct(start)));
</script>

<div class="dual-range" aria-labelledby={ariaLabelledBy}>
	<p id="{sliderId}-value" class="dual-range__range-text">{rangeText}</p>

	<div class="dual-range__track-wrap">
		<div class="dual-range__track" style:--fill-left="{fillLeft}%" style:--fill-width="{fillWidth}%">
			<div
				class="dual-range__segment dual-range__segment--start"
				style:left="0"
				style:width="{startSegWidthPct}%"
			>
				<input
					id="{sliderId}-start"
					data-testid="{sliderId}-range-start"
					class="dual-range__input dual-range__input--start"
					type="range"
					min={min}
					max={startInputMax}
					step={step}
					value={start}
					aria-label="Início do intervalo"
					aria-valuemin={min}
					aria-valuemax={startInputMax}
					aria-valuenow={start}
					oninput={onStartInput}
				/>
			</div>
			<div
				class="dual-range__segment dual-range__segment--end"
				style:left="{endSegLeftPct}%"
				style:width="{endSegWidthPct}%"
			>
				<input
					id="{sliderId}-end"
					data-testid="{sliderId}-range-end"
					class="dual-range__input dual-range__input--end"
					type="range"
					min={endInputMin}
					max={max}
					step={step}
					value={end}
					aria-label="Fim do intervalo"
					aria-valuemin={endInputMin}
					aria-valuemax={max}
					aria-valuenow={end}
					oninput={onEndInput}
				/>
			</div>
		</div>
	</div>

	<div class="dual-range__ticks" aria-hidden="true">
		<span class="dual-range__tick dual-range__tick--min">{minL}</span>
		<span class="dual-range__tick dual-range__tick--max">{maxL}</span>
	</div>
</div>

<style>
	.dual-range {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
		min-width: 0;
		width: 100%;
	}

	.dual-range__range-text {
		margin: 0;
		text-align: center;
		font-size: var(--text-meta);
		font-weight: var(--font-weight-semibold);
		color: var(--color-primary);
		line-height: 1.3;
	}

	.dual-range__track-wrap {
		position: relative;
		padding-block: var(--space-sm);
	}

	.dual-range__segment {
		position: absolute;
		top: 0;
		height: var(--space-md);
		min-width: 0;
	}

	.dual-range__track {
		position: relative;
		height: var(--space-md);
		border-radius: var(--radius-sm);
		background: linear-gradient(
			to right,
			var(--color-border) 0,
			var(--color-border) var(--fill-left),
			var(--color-primary) var(--fill-left),
			var(--color-primary) calc(var(--fill-left) + var(--fill-width)),
			var(--color-border) calc(var(--fill-left) + var(--fill-width)),
			var(--color-border) 100%
		);
	}

	.dual-range__input {
		position: absolute;
		left: 0;
		width: 100%;
		height: var(--space-md);
		margin: 0;
		padding: 0;
		background: none;
		pointer-events: none;
		-webkit-appearance: none;
		appearance: none;
	}

	.dual-range__input::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		pointer-events: auto;
		width: 1.125rem;
		height: 1.125rem;
		border-radius: 50%;
		background: var(--color-background);
		border: 2px solid var(--color-primary);
		box-shadow: var(--shadow-sm);
		cursor: grab;
	}

	.dual-range__input::-moz-range-thumb {
		pointer-events: auto;
		width: 1.125rem;
		height: 1.125rem;
		border-radius: 50%;
		background: var(--color-background);
		border: 2px solid var(--color-primary);
		box-shadow: var(--shadow-sm);
		cursor: grab;
	}

	.dual-range__input:active::-webkit-slider-thumb {
		cursor: grabbing;
	}

	.dual-range__input:active::-moz-range-thumb {
		cursor: grabbing;
	}

	.dual-range__input:focus-visible::-webkit-slider-thumb {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}

	.dual-range__input:focus-visible::-moz-range-thumb {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}

	.dual-range__input::-webkit-slider-runnable-track {
		height: var(--space-md);
		background: transparent;
		border: none;
	}

	.dual-range__input::-moz-range-track {
		height: var(--space-md);
		background: transparent;
		border: none;
	}

	/* End thumb above start when thumbs overlap so the upper bound stays grabbable. */
	.dual-range__input--start {
		z-index: 3;
	}

	.dual-range__input--end {
		z-index: 4;
	}

	.dual-range__ticks {
		display: flex;
		justify-content: space-between;
		gap: var(--space-sm);
		font-size: var(--text-caption);
		font-weight: var(--font-weight-regular);
		color: var(--color-text-secondary);
		line-height: 1.3;
	}

	.dual-range__tick--min {
		text-align: left;
	}

	.dual-range__tick--max {
		text-align: right;
	}
</style>

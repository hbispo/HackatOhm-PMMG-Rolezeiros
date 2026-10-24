<script setup lang="ts">
import { computed } from 'vue'
import { usePlano } from '../stores/plano'
import { corViatura } from '../cores'

const plano = usePlano()

const metricas = computed(() => plano.distribuicao?.metricas)
const antes = computed(() => plano.anterior?.metricas)

function delta(atual?: number, anterior?: number): string {
  if (atual === undefined || anterior === undefined) return ''
  const d = Math.round((atual - anterior) * 10) / 10
  return d === 0 ? '' : `${d > 0 ? '+' : ''}${d} p.p.`
}
</script>

<template>
  <section class="painel">
    <h2>Cenário</h2>
    <div class="cenarios">
      <button @click="plano.aplicarCenario(1)">1 · Todas</button>
      <button @click="plano.aplicarCenario(2)">2 · Uma empenhada</button>
      <button @click="plano.aplicarCenario(3)">3 · Várias</button>
    </div>

    <h2>Cobertura</h2>
    <div v-if="metricas" class="metricas">
      <div>
        <strong>{{ metricas.cobertura_risco_pct }}%</strong>
        <span>do risco ponderado</span>
        <em :class="{ ruim: (metricas.cobertura_risco_pct ?? 0) < (antes?.cobertura_risco_pct ?? 0) }">
          {{ delta(metricas.cobertura_risco_pct, antes?.cobertura_risco_pct) }}
        </em>
      </div>
      <div>
        <strong>{{ metricas.cobertura_area_pct }}%</strong>
        <span>da área</span>
        <em :class="{ ruim: (metricas.cobertura_area_pct ?? 0) < (antes?.cobertura_area_pct ?? 0) }">
          {{ delta(metricas.cobertura_area_pct, antes?.cobertura_area_pct) }}
        </em>
      </div>
    </div>

    <h2>Viaturas <small>{{ plano.disponiveis.length }}/{{ plano.viaturas.length }} disponíveis</small></h2>
    <ul class="viaturas">
      <li
        v-for="v in plano.viaturas"
        :key="v.id"
        :class="{ empenhada: !v.disponivel, selecionada: plano.viaturaSelecionada === v.id }"
        @click="v.disponivel && (plano.viaturaSelecionada = plano.viaturaSelecionada === v.id ? null : v.id)"
      >
        <i :style="{ background: corViatura(v.id, plano.viaturas) }" />
        <div>
          <b>{{ v.nome }}</b>
          <small>{{ v.tipo === 'atendimento' ? 'Atendimento' : 'Preventiva' }}</small>
        </div>
        <button @click.stop="plano.alternarDisponibilidade(v.id)">
          {{ v.disponivel ? 'Empenhar' : 'Liberar' }}
        </button>
      </li>
    </ul>

    <h2>Faixa horária</h2>
    <select v-model="plano.horaSelecionada">
      <option :value="null">Todas</option>
      <option v-for="f in plano.faixas" :key="f.hora" :value="f.hora">
        {{ String(f.hora).padStart(2, '0') }}h · Classe {{ f.classe }}
      </option>
    </select>
  </section>
</template>

<style scoped>
.painel { padding: 12px 16px; overflow-y: auto; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--dourado-escuro); margin: 18px 0 8px; }
h2 small { text-transform: none; letter-spacing: 0; color: var(--texto-suave); font-weight: normal; }
.cenarios { display: flex; gap: 6px; flex-wrap: wrap; }
.metricas { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.metricas div { background: var(--fundo); padding: 8px; border-radius: 6px; display: grid; }
.metricas strong { font-size: 22px; }
.metricas span { font-size: 12px; color: var(--texto-suave); }
.metricas em { font-size: 12px; font-style: normal; color: #2a7a2a; min-height: 1em; }
.metricas em.ruim { color: #d00000; }
.viaturas { list-style: none; padding: 0; margin: 0; display: grid; gap: 6px; }
.viaturas li {
  display: grid; grid-template-columns: 14px 1fr auto; gap: 10px; align-items: center;
  padding: 8px; border: 1px solid var(--borda); border-radius: 6px; cursor: pointer;
}
.viaturas li.selecionada { border-color: var(--dourado); background: var(--fundo); }
.viaturas li.empenhada { opacity: .55; cursor: default; }
.viaturas li.empenhada b { text-decoration: line-through; }
.viaturas i { width: 14px; height: 14px; border-radius: 50%; }
.viaturas small { display: block; color: var(--texto-suave); font-size: 12px; }
select { width: 100%; }
</style>

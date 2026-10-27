<script setup lang="ts">
import { computed } from 'vue'
import { usePlano } from '../stores/plano'
import { corViatura } from '../cores'

const plano = usePlano()

const mudanca = computed(() => plano.estado?.mudanca)
const cargaPorViatura = computed(() => new Map((plano.estado?.carga ?? []).map((c) => [c.viatura, c])))
const problemas = computed(() => plano.estado?.problemas ?? [])

const RAIOS = ['1km', '2km', '3km'] as const
const cobertura = computed(() => plano.estado?.cobertura)
const coberturaAntes = computed(() => mudanca.value?.cobertura_antes)

function delta(atual: number, antes?: number): string {
  if (antes === undefined) return ''
  const d = Math.round((atual - antes) * 10) / 10
  return d === 0 ? '=' : `${d > 0 ? '+' : ''}${d}`
}
</script>

<template>
  <section class="painel" :class="{ ocupado: plano.ocupado }">
    <h2>Cenário <small v-if="plano.estado">atual: {{ plano.estado.cenario }}</small></h2>
    <div class="cenarios">
      <button :disabled="plano.ocupado" @click="plano.aplicarCenario(1)">1 · Todas</button>
      <button :disabled="plano.ocupado" @click="plano.aplicarCenario(2)">2 · Uma empenhada</button>
      <button :disabled="plano.ocupado" @click="plano.aplicarCenario(3)">3 · Duas</button>
    </div>

    <h2>Cobertura territorial</h2>
    <table v-if="cobertura" class="cobertura">
      <thead>
        <tr><th>Até</th><th>% hexágonos</th><th>% pontos</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in RAIOS" :key="r">
          <td>{{ r.replace('km', ' km') }}</td>
          <td>
            {{ cobertura[r].pct_hexagonos }}%
            <em :class="{ ruim: cobertura[r].pct_hexagonos < (coberturaAntes?.[r].pct_hexagonos ?? 0) }">
              {{ delta(cobertura[r].pct_hexagonos, coberturaAntes?.[r].pct_hexagonos) }}
            </em>
          </td>
          <td>
            {{ cobertura[r].pct_pontos }}%
            <em :class="{ ruim: cobertura[r].pct_pontos < (coberturaAntes?.[r].pct_pontos ?? 0) }">
              {{ delta(cobertura[r].pct_pontos, coberturaAntes?.[r].pct_pontos) }}
            </em>
          </td>
        </tr>
      </tbody>
    </table>
    <p class="nota-cobertura">Distância do centro do hexágono ao hexágono-base da viatura mais próxima.</p>

    <template v-if="mudanca">
      <h2>Última mudança</h2>
      <div class="mudanca">
        <p>
          <b>{{ mudanca.viaturas.join(', ') }}</b>
          {{ mudanca.acao === 'empenhar' ? (mudanca.viaturas.length > 1 ? 'empenhadas' : 'empenhada') : 'liberada' }}
        </p>
        <div v-if="mudanca.acao === 'empenhar'" class="numeros">
          <div><strong>{{ mudanca.hex_descobertos.length }}</strong><span>hexágonos descobertos</span></div>
          <div><strong>{{ mudanca.pct_pontos_descobertos }}%</strong><span>dos pontos estavam lá</span></div>
        </div>
        <p class="nota">{{ mudanca.hex_mudaram.length }} hexágonos mudaram de viatura (contorno vermelho no mapa)</p>
      </div>
    </template>

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
          <b>{{ v.id }}</b>
          <small>
            {{ v.tipo === 'atendimento' ? 'Atendimento' : 'Preventiva' }}
            <template v-if="cargaPorViatura.get(v.id)">
              · {{ cargaPorViatura.get(v.id)!.hexagonos }} hex · {{ cargaPorViatura.get(v.id)!.pct_pontos }}% dos pontos
              · alcance {{ cargaPorViatura.get(v.id)!.dist_max_km }} km
            </template>
          </small>
        </div>
        <button :disabled="plano.ocupado" @click.stop="plano.alternarDisponibilidade(v.id)">
          {{ v.disponivel ? 'Empenhar' : 'Liberar' }}
        </button>
      </li>
    </ul>

    <h2>Faixa horária</h2>
    <select v-model="plano.horaSelecionada">
      <option :value="null">Todas</option>
      <option v-for="f in plano.faixas" :key="f.hora" :value="f.hora">
        {{ String(f.hora).padStart(2, '0') }}h · Classe {{ f.classe }} · {{ f.pontos }} pontos
      </option>
    </select>

    <h2>Regras do Cartão-Programa</h2>
    <p v-if="!problemas.length" class="ok">✓ Todas as regras do edital cumpridas</p>
    <ul v-else class="problemas">
      <li v-for="p in problemas" :key="p">{{ p }}</li>
    </ul>
  </section>
</template>

<style scoped>
.painel { padding: 12px 16px; overflow-y: auto; }
.painel.ocupado { cursor: progress; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--dourado-escuro); margin: 18px 0 8px; }
h2 small { text-transform: none; letter-spacing: 0; color: var(--texto-suave); font-weight: normal; }
.cenarios { display: flex; gap: 6px; flex-wrap: wrap; }
.cobertura { width: 100%; border-collapse: collapse; font-size: 13px; }
.cobertura th { text-align: left; font-size: 11px; color: var(--texto-suave); font-weight: 600; padding: 2px 4px; }
.cobertura td { padding: 3px 4px; border-top: 1px solid var(--borda); }
.cobertura em { font-style: normal; font-size: 11px; color: #2a7a2a; }
.cobertura em.ruim { color: #d00000; }
.nota-cobertura { font-size: 11px; color: var(--texto-suave); margin: 4px 0 0; }
.mudanca { background: var(--fundo); border-left: 3px solid #d00000; border-radius: 6px; padding: 8px 10px; font-size: 13px; }
.mudanca p { margin: 0 0 6px; }
.mudanca .nota { margin: 6px 0 0; color: var(--texto-suave); font-size: 12px; }
.numeros { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.numeros div { display: grid; }
.numeros strong { font-size: 20px; }
.numeros span { font-size: 12px; color: var(--texto-suave); }
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
.ok { color: #2a7a2a; font-size: 13px; margin: 0; }
.problemas { color: #d00000; font-size: 12px; padding-left: 18px; margin: 0; }
button:disabled { opacity: .5; cursor: progress; }
</style>

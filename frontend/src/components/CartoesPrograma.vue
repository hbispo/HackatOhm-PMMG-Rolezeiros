<script setup lang="ts">
import { computed } from 'vue'
import { usePlano } from '../stores/plano'
import { ROTULO_MODO, corViatura } from '../cores'
import type { FaixaCartao } from '../types'

const plano = usePlano()

const cartoes = computed(() =>
  plano.viaturaSelecionada
    ? plano.cartoes.filter((c) => c.viatura === plano.viaturaSelecionada)
    : plano.cartoes,
)

const imprimir = () => window.print()

function atividade(f: FaixaCartao) {
  return f.modo === 'ponto_base'
    ? `Ponto-base ${f.ponto_base_min}' + patrulha ${f.patrulha_min}' · ${f.raio_km} km`
    : `${ROTULO_MODO[f.modo]} · ${f.patrulha_min}'`
}

function selecionarHora(hora: number) {
  plano.horaSelecionada = plano.horaSelecionada === hora ? null : hora
}
</script>

<template>
  <section class="cartoes">
    <header>
      <h2>Cartões-Programa <small>({{ cartoes.length }})</small></h2>
      <button @click="imprimir">Imprimir</button>
    </header>
    <article
      v-for="c in cartoes"
      :key="c.viatura"
      class="cartao"
      :style="{ borderTopColor: corViatura(c.viatura, plano.viaturas) }"
    >
      <h3>
        {{ c.viatura }}
        <small>{{ c.tipo === 'atendimento' ? 'Atendimento' : 'Preventiva' }} · base no hexágono {{ c.hex_base }} · {{ c.qtd_hexagonos_area }} hexágonos</small>
      </h3>
      <table>
        <thead>
          <tr><th>Faixa</th><th>Cl.</th><th>Atividade</th><th>Destaque</th><th>% área</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="f in c.faixas"
            :key="f.hora"
            :class="[`classe-${f.classe}`, { ativa: plano.horaSelecionada === f.hora }]"
            :title="`${f.descricao}\nOrigem do destaque: ${f.origem_destaque}`"
            @click="selecionarHora(f.hora)"
          >
            <td>{{ String(f.hora).padStart(2, '0') }}h–{{ String((f.hora + 1) % 24).padStart(2, '0') }}h</td>
            <td><span class="classe">{{ f.classe }}</span></td>
            <td>{{ atividade(f) }}</td>
            <td>{{ f.hexagonos_destaque.join(', ') }}</td>
            <td>{{ f.pct_da_area }}%</td>
          </tr>
        </tbody>
      </table>
    </article>
  </section>
</template>

<style scoped>
.cartoes { padding: 12px 16px; overflow-y: auto; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--dourado-escuro); margin: 6px 0; }
.cartao { border: 1px solid var(--borda); border-top: 4px solid; border-radius: 6px; margin: 12px 0; padding: 8px 10px; break-inside: avoid; }
h3 { margin: 4px 0 8px; font-size: 16px; }
h3 small { display: block; font-size: 12px; font-weight: normal; color: var(--texto-suave); }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; color: var(--texto-suave); font-weight: 600; border-bottom: 1px solid var(--borda); padding: 4px; }
td { padding: 3px 4px; border-bottom: 1px solid var(--fundo); }
tbody tr { cursor: pointer; }
tr.ativa td { background: #fff3c4; }
.classe { display: inline-block; width: 18px; text-align: center; border-radius: 3px; font-weight: 700; }
.classe-1 .classe { background: #1c1c1c; color: #fff; }
.classe-2 .classe { background: var(--dourado); color: #1c1c1c; }
.classe-3 .classe { background: #e6e1d6; color: #1c1c1c; }
</style>

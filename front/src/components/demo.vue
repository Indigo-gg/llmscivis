<template>

  <div>
    <div ref="vtkContainer"/>
    <div class="box">
      <div class="select">
        <select
            style="width: 5vw"
            :value="representation"
            @change="setRepresentation($event.target.value)"
        >
          <option value="0">点图</option>
          <option value="1">线图</option>
          <option value="2">面图</option>
        </select>
      </div>
      <div class="input">
        <input
            type="range"
            min="4"
            max="80"
            :value="coneResolution"
            @input="setConeResolution($event.target.value)"
        />
      </div>
    </div>

  </div>
</template>

<script>

import {onBeforeUnmount, onMounted, ref, unref, watchEffect} from "vue";
import vtkFullScreenRenderWindow from "@kitware/vtk.js/Rendering/Misc/FullScreenRenderWindow";
import vtkConeSource from "@kitware/vtk.js/Filters/Sources/ConeSource";
import vtkMapper from "@kitware/vtk.js/Rendering/Core/Mapper";
import vtkActor from "@kitware/vtk.js/Rendering/Core/Actor";

import '@kitware/vtk.js/Rendering/Profiles/Geometry';
export default {
  name: "Demo",
  setup(){
    const vtkContainer=ref(null)//container of vtk
    const context = ref(null)
    const coneResolution=ref(6)
    const representation = ref(2)

    /**
     * 这两个函数是干什么用的
     * @param res
     */
    function setConeResolution(res) {
      coneResolution.value = Number(res)
    }

    function setRepresentation(rep){
      representation.value = Number(rep)
    }
    watchEffect(()=>{
      const res = unref(coneResolution)
      const rep = unref(representation)
      if(context.value){
        const {actor, coneSource, renderWindow }=context.value
        coneSource.setResolution(res)
        actor.getProperty().setRepresentation(rep)
        renderWindow.render()
      }
    });

    onMounted(() =>{
      if(!context.value) {//如果没有context的话
        const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({
          rootContainer: vtkContainer.value
        })
        const coneSource = vtkConeSource.newInstance({height:1.0})
        const mapper = vtkMapper.newInstance();
        mapper.setInputConnection(coneSource.getOutputPort())

        const actor =vtkActor.newInstance()
        actor.setMapper(mapper)
        const renderer = fullScreenRenderer.getRenderer()

        const renderWindow =fullScreenRenderer.getRenderWindow()

        renderer.addActor(actor)
        renderer.resetCamera()
        renderWindow.render()

        context.value = {
          fullScreenRenderer,
          renderWindow,
          renderer,
          coneSource,
          actor,
          mapper
        }
      }
    })
    onBeforeUnmount(()=>{
      if(context.value) {
        const {fullScreenRenderer,coneSource,actor,mapper}=context.value
        actor.delete()
        mapper.delete()
        coneSource.delete()
        fullScreenRenderer.delete()
        context.value = null
      }
    })

    return {
      vtkContainer,
      setRepresentation,
      coneResolution,
      setConeResolution,
      representation
    }

  }
}
</script>

<style scoped>
.box{
  position: absolute;
  top: 20px;
  left: 10px;
}
.select{

}
</style>

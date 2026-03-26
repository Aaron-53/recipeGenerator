import React from 'react'

export default function RecipeCard({ recipe, anchorId }) {
  if (!recipe) return null

  const ingredients = Array.isArray(recipe.ingredients) ? recipe.ingredients : []
  const steps = Array.isArray(recipe.steps) ? recipe.steps : []
  const tips = recipe.tips != null ? String(recipe.tips) : ''

  return (
    <article
      id={anchorId || undefined}
      className="mt-2 w-full scroll-mt-4 rounded-2xl border border-[#5C6E43]/60 bg-[#FCFAE6] px-4 py-3 text-[#3d2b1f] shadow-sm"
    >
      <h3 className="text-lg font-semibold text-[#5C6E43] mb-2">
        {recipe.recipe_name || 'Recipe'}
      </h3>

      {ingredients.length > 0 && (
        <div className="mb-3">
          <h4 className="text-sm font-medium uppercase tracking-wide text-[#3d2b1f]/90 mb-1">
            Ingredients
          </h4>
          <ul className="list-disc list-inside space-y-0.5 text-sm pl-4">
            {ingredients.map((ing, j) => (
              <li key={j}>{ing}</li>
            ))}
          </ul>
        </div>
      )}

      {steps.length > 0 && (
        <div className="mb-3">
          <h4 className="text-sm font-medium uppercase tracking-wide text-[#3d2b1f]/90 mb-1">
            Steps
          </h4>
          <ol className="list-decimal list-inside space-y-1 text-sm pl-4">
            {steps.map((step, j) => (
              <li key={j}>
                {step}
              </li>
            ))}
          </ol>
        </div>
      )}

      {tips && (
        <p className="text-sm border-t border-[#e8dcc4] pt-2 mt-1">
          <span className="font-semibold text-[#5C6E43] px-3">Tip:</span>
          {tips}
        </p>
      )}
    </article>
  )
}

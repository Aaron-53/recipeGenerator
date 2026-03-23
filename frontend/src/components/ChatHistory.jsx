import React from 'react'

const ChatHistory = ({ titles = [], activeIndex = 0, onSelect }) => {
  const hasHistory = Array.isArray(titles) && titles.length > 0

  return (
    <aside
      className="flex w-full min-w-0 flex-col rounded-[24px] bg-[#F6E7C8] shadow-md overflow-hidden md:w-[28%] md:min-w-[200px] md:max-w-[320px] h-[calc(100vh-9rem)]"
    >
      <div className="rounded-t-[24px] bg-[#F6C7B7] px-4 py-4 text-center shrink-0">
        <h2 className="text-[#5C6E43] font-semibold text-lg sm:text-2xl">
          Chat history
        </h2>
      </div>
      {hasHistory ? (
        <ul className="flex-1 overflow-y-auto p-2 space-y-1.5 chat-history-scroll min-h-0">
          {titles.map((title, index) => (
            <li key={`${title}-${index}`}>
              <button
                type="button"
                onClick={() => onSelect?.(index)}
                className={`w-full text-left rounded-xl truncate p-3 text-sm font-medium text-[#5C6E43] transition-colors ${
                  index === activeIndex
                    ? 'bg-[#f0ddb6]'
                    : 'bg-[#F6E7C8] hover:bg-[#f0ddb6]/50'
                }`}
              >
                {title}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center px-5 py-10 text-center min-h-0">
          <p className="text-[#3d2b1f]/70 text-sm leading-relaxed max-w-[220px]">
            No history to show yet.
          </p>
          <p className="text-[#5b6d44] font-semibold text-sm sm:text-base mt-3">
            Start cooking today!
          </p>
        </div>
      )}
    </aside>
  )
}

export default ChatHistory

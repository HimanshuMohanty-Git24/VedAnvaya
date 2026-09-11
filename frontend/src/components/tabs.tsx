"use client";

import * as RadixTabs from "@radix-ui/react-tabs";

export type TabDef = { value: string; label: string; badge?: number | null };

export function Tabs({
    tabs,
    defaultValue,
    label,
    children,
}: {
    tabs: TabDef[];
    defaultValue?: string;
    label: string;
    children: React.ReactNode;
}) {
    return (
        <RadixTabs.Root className="tabs" defaultValue={defaultValue ?? tabs[0]?.value}>
            <RadixTabs.List className="tab-list" aria-label={label}>
                {tabs.map((tab) => (
                    <RadixTabs.Trigger className="tab-trigger" key={tab.value} value={tab.value}>
                        {tab.label}
                        {tab.badge != null && <span className="tab-badge">{tab.badge}</span>}
                    </RadixTabs.Trigger>
                ))}
            </RadixTabs.List>
            {children}
        </RadixTabs.Root>
    );
}

export function TabPanel({ value, children }: { value: string; children: React.ReactNode }) {
    return (
        <RadixTabs.Content className="tab-panel" value={value}>
            {children}
        </RadixTabs.Content>
    );
}

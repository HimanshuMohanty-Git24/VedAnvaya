import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { DeitiesPlate, isCertainty } from "@/components/lab/plates/deities";
import { FormulasPlate } from "@/components/lab/plates/formulas";
import { FourCorporaPlate, isScale } from "@/components/lab/plates/four-corpora";
import { HumanConcernsPlate } from "@/components/lab/plates/human-concerns";
import { MaterialCulturePlate, isCategory } from "@/components/lab/plates/material-culture";
import { RitualPlate } from "@/components/lab/plates/ritual";
import { TransmissionPlate } from "@/components/lab/plates/transmission";
import { PLATES, PLATES_BY_SLUG, type PlateSlug } from "@/lib/lab";

/**
 * One plate per route.
 *
 * The dispatch is a switch rather than a registry of components, because a registry would let
 * a slug exist in the catalogue with no implementation behind it and fail at runtime. Here the
 * switch is exhaustive over `PlateSlug`, so adding a slug to the catalogue without writing its
 * plate is a type error at build time.
 *
 * Everything below this point renders on the server. The Lab ships no client JavaScript of its
 * own: the controls are links, the reveals are `<details>`, and the figures are tables.
 */

export const revalidate = 300;

type Params = {
    params: Promise<{ plate: string }>;
    searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export function generateStaticParams() {
    return PLATES.map((plate) => ({ plate: plate.slug }));
}

function resolve(slug: string) {
    return (PLATES_BY_SLUG as Record<string, (typeof PLATES)[number]>)[slug] ?? null;
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
    const { plate: slug } = await params;
    const plate = resolve(slug);
    if (!plate) return { title: "Not found" };
    const description = `${plate.question} ${plate.summary}`;
    return {
        title: plate.title,
        description,
        openGraph: { title: `${plate.title} | VedAnvaya`, description },
    };
}

/** A search param arrives as `string | string[]`; only the first value is ever meaningful here. */
function one(value: string | string[] | undefined) {
    return Array.isArray(value) ? value[0] : value;
}

export default async function PlatePage({ params, searchParams }: Params) {
    const [{ plate: slug }, query] = await Promise.all([params, searchParams]);
    const plate = resolve(slug);
    if (!plate) notFound();

    const scale = one(query.scale);
    const certainty = one(query.certainty);
    const category = one(query.category);

    return (
        <div className="va-plate-page">
            <Figure
                category={isCategory(category) ? category : undefined}
                certainty={isCertainty(certainty) ? certainty : undefined}
                scale={isScale(scale) ? scale : undefined}
                slug={plate.slug}
            />
        </div>
    );
}

function Figure({
    slug,
    scale,
    certainty,
    category,
}: {
    slug: PlateSlug;
    scale?: Parameters<typeof FourCorporaPlate>[0]["scale"];
    certainty?: Parameters<typeof DeitiesPlate>[0]["certainty"];
    category?: Parameters<typeof MaterialCulturePlate>[0]["category"];
}) {
    switch (slug) {
        case "four-corpora":
            return <FourCorporaPlate scale={scale} />;
        case "deities":
            return <DeitiesPlate certainty={certainty} />;
        case "transmission":
            return <TransmissionPlate />;
        case "formulas":
            return <FormulasPlate />;
        case "human-concerns":
            return <HumanConcernsPlate />;
        case "ritual":
            return <RitualPlate />;
        case "material-culture":
            return <MaterialCulturePlate category={category} />;
    }
}
